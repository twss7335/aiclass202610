"""Browser inference must numerically match the trained Python models."""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

import numpy as np

from src.ai4i.workflow import (
    FEATURE_COLUMNS as AI4I_COLUMNS,
    TARGET,
    _features,
    _fit_model,
    _pipeline,
    balanced_weights,
    load_data,
    make_split,
)
from src.iris_workflow import CLASS_ORDER, FEATURE_COLUMNS, build_model, load_iris_csv, split_data


ROOT = Path(__file__).resolve().parents[1]
NODE = os.environ.get("NODE_BIN") or shutil.which("node")


@unittest.skipUnless(NODE, "Node.js is required for front-end parity checks")
class FrontendInferenceTests(unittest.TestCase):
    @staticmethod
    def run_js(kind, rows):
        script = (
            "const fs=require('fs');"
            "const app=require('./docs/app.js');"
            "const rows=JSON.parse(fs.readFileSync(0,'utf8'));"
            "console.log(JSON.stringify(rows.map(row=>kind==='iris'?app.predictIris(row):app.predictAI4I(row))));"
        )
        script = "const kind=" + json.dumps(kind) + ";" + script
        result = subprocess.run(
            [NODE, "-e", script], input=json.dumps(rows), text=True,
            capture_output=True, cwd=ROOT, check=True,
        )
        return json.loads(result.stdout)

    def test_iris_probabilities_match_python_mlp(self):
        frame = load_iris_csv(ROOT / "data" / "iris.csv")
        X_train, X_test, y_train, _ = split_data(frame)
        labels = {name: i for i, name in enumerate(CLASS_ORDER)}
        model = build_model()
        model.fit(X_train, y_train.map(labels))
        sample = X_test.iloc[:5]
        actual = self.run_js("iris", sample.to_dict(orient="records"))
        expected = model.predict_proba(sample)
        for row, probabilities in zip(actual, expected):
            self.assertEqual(row["className"], CLASS_ORDER[int(np.argmax(probabilities))])
            np.testing.assert_allclose(row["probabilities"], probabilities, rtol=0, atol=1e-8)

    def test_ai4i_probabilities_match_python_forest(self):
        frame = load_data(ROOT / "data" / "ai4i" / "ai4i2020.csv")
        train_idx, test_idx = make_split(frame)
        train = frame.iloc[train_idx]
        y = train[TARGET].to_numpy()
        weights = balanced_weights(y)
        model = _fit_model(_pipeline("forest", "engineered", 42, weights), "forest",
                           _features(train, "engineered"), y, weights)
        sample = frame.iloc[test_idx[:5]][AI4I_COLUMNS]
        actual = self.run_js("ai4i", sample.to_dict(orient="records"))
        expected = model.predict_proba(_features(sample, "engineered"))[:, 1]
        for row, probability in zip(actual, expected):
            self.assertAlmostEqual(row["failureProbability"], float(probability), places=8)

    def test_both_forms_share_one_result_region(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('id="result"'), 1)
        self.assertIn('id="iris-form"', html)
        self.assertIn('id="ai4i-form"', html)
        self.assertEqual(html.count('src="app.js"'), 1)


if __name__ == "__main__":
    unittest.main()
