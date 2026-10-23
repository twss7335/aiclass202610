"""Executable contracts for the conclusions reported by the AI experiments."""

import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.ai4i.workflow import (
    DERIVED_COLUMNS,
    FAILURE_MODES,
    FEATURE_COLUMNS,
    NUMERIC_COLUMNS,
    SEED,
    TARGET,
    _features,
    _fit_model,
    _pipeline,
    balanced_weights,
    load_data,
    make_split,
)


ROOT = Path(__file__).resolve().parents[1]


class ExperimentConclusionTests(unittest.TestCase):
    def test_feature_contract_excludes_failure_labels(self):
        forbidden = {TARGET, *FAILURE_MODES}
        leaked = forbidden.intersection(FEATURE_COLUMNS)
        self.assertFalse(leaked, f"Target leakage in feature list: {sorted(leaked)}")

    def test_selected_model_does_not_collapse_to_majority_class(self):
        metrics = json.loads(
            (ROOT / "results" / "ai4i" / "metrics.json").read_text(encoding="utf-8")
        )
        predictions = pd.read_csv(ROOT / "results" / "ai4i" / "test_predictions.csv")
        self.assertGreater(metrics["recall"], 0, "Failure recall must be greater than zero")
        self.assertGreater(
            predictions["predicted"].nunique(),
            1,
            "Predictions collapsed to a single class",
        )

    def test_every_published_number_matches_its_source_result_report(self):
        published = json.loads((ROOT / "docs" / "results.json").read_text(encoding="utf-8"))
        for study, payload in published.items():
            source = json.loads((ROOT / payload["source"]).read_text(encoding="utf-8"))
            self.assertEqual(
                payload["metrics"],
                source,
                f"Published {study} numbers differ from {payload['source']}",
            )

    def test_saved_preprocessing_parameters_reproduce_pipeline_predictions(self):
        artifact_path = ROOT / "results" / "ai4i" / "preprocessing.json"
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        frame = load_data(ROOT / "data" / "ai4i" / "ai4i2020.csv")
        train_positions, test_positions = make_split(frame)
        train = frame.iloc[train_positions]
        labels = train[TARGET].to_numpy()
        weights = balanced_weights(labels)
        model = _fit_model(
            _pipeline("forest", "engineered", SEED, weights),
            "forest",
            _features(train, "engineered"),
            labels,
            weights,
        )

        sample = _features(frame.iloc[test_positions[:3]], "engineered")
        expected = model.predict_proba(sample)
        self.assertEqual(artifact["numeric_features"], [*NUMERIC_COLUMNS, *DERIVED_COLUMNS])
        numeric = sample[artifact["numeric_features"]].to_numpy(dtype=float)
        scaled = (numeric - np.asarray(artifact["mean"])) / np.asarray(artifact["std"])
        categories = artifact["type_categories"]
        encoded = np.column_stack([
            sample["Type"].to_numpy() == category for category in categories
        ]).astype(float)
        transformed = np.column_stack([scaled, encoded])
        actual = model.named_steps["model"].predict_proba(transformed)
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
