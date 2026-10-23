import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai4i.workflow import (  # noqa: E402
    FEATURE_COLUMNS,
    FAILURE_MODES,
    audit_data,
    balanced_weights,
    choose_threshold,
    engineer_features,
    evaluate_scores,
    load_data,
    make_split,
    pca_projection,
)
from src.ai4i.workflow import _features, _pipeline


class AI4IContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "data" / "ai4i" / "ai4i2020.csv"

    def test_official_data_contract_and_leakage_exclusions(self):
        frame = load_data(self.path)
        self.assertEqual(len(frame), 10000)
        self.assertTrue(set(FEATURE_COLUMNS).issubset(frame.columns))
        self.assertTrue(set(FAILURE_MODES).issubset(frame.columns))
        self.assertFalse(set(FEATURE_COLUMNS) & {"UDI", "UID", "Product ID", "Machine failure", *FAILURE_MODES})
        self.assertEqual(set(frame["Machine failure"].unique()), {0, 1})

    def test_audit_reports_label_inconsistency_without_mutating_data(self):
        frame = load_data(self.path)
        original = frame.copy(deep=True)
        report = audit_data(frame)
        self.assertEqual(report["rows"], 10000)
        self.assertEqual(report["missing_total"], 0)
        self.assertEqual(sum(report["class_counts"].values()), 10000)
        self.assertEqual(set(report["mode_counts"]), set(FAILURE_MODES))
        self.assertTrue(frame.equals(original))
        self.assertIn("failure_without_mode", report)
        self.assertIn("mode_without_failure", report)

    def test_physical_feature_formulas(self):
        frame = pd.DataFrame({
            "Air temperature [K]": [300.0],
            "Process temperature [K]": [310.0],
            "Rotational speed [rpm]": [60],
            "Torque [Nm]": [10.0],
            "Tool wear [min]": [100],
            "Type": ["L"],
        })
        enriched = engineer_features(frame)
        self.assertAlmostEqual(enriched["temperature_difference_K"].iloc[0], 10)
        self.assertAlmostEqual(enriched["power_W"].iloc[0], 20 * np.pi)
        self.assertAlmostEqual(enriched["wear_torque_minNm"].iloc[0], 1000)

    def test_split_is_stratified_reproducible_and_disjoint(self):
        frame = load_data(self.path)
        first = make_split(frame, seed=42)
        second = make_split(frame, seed=42)
        self.assertEqual(first[0].tolist(), second[0].tolist())
        self.assertEqual(len(first[0]) + len(first[1]), len(frame))
        self.assertFalse(set(first[0]) & set(first[1]))
        global_rate = frame["Machine failure"].mean()
        self.assertLess(abs(frame.iloc[first[1]]["Machine failure"].mean() - global_rate), 0.01)

    def test_weights_are_derived_from_only_supplied_fold(self):
        y = np.array([0, 0, 0, 1])
        weights = balanced_weights(y)
        self.assertAlmostEqual(weights[0], 2 / 3)
        self.assertAlmostEqual(weights[1], 2)

    def test_preprocessor_is_fit_on_supplied_training_rows_only(self):
        frame = load_data(self.path)
        train_idx, test_idx = make_split(frame)
        X_train = _features(frame.iloc[train_idx], "raw")
        y_train = frame.iloc[train_idx]["Machine failure"].to_numpy()
        model = _pipeline("dummy", "raw", 42, balanced_weights(y_train))
        model.fit(X_train, y_train)
        scaler = model.named_steps["preprocess"].named_transformers_["numeric"]
        self.assertAlmostEqual(scaler.mean_[0], X_train["Air temperature [K]"].mean())
        self.assertNotAlmostEqual(scaler.mean_[0], frame.iloc[test_idx]["Air temperature [K]"].mean())

    def test_pca_uses_numeric_operating_features_and_variance_contract(self):
        frame = load_data(self.path)
        points, ratio = pca_projection(frame)
        self.assertEqual(points.shape, (10000, 2))
        self.assertEqual(len(ratio), 2)
        self.assertGreater(ratio[0], 0)
        self.assertLessEqual(sum(ratio), 1.0000001)

    def test_pr_auc_uses_scores_and_threshold_uses_validation_only(self):
        y = np.array([0, 1, 0, 1, 0, 1])
        scores = np.array([0.05, 0.90, 0.65, 0.40, 0.20, 0.75])
        threshold = choose_threshold(y, scores, target_recall=1.0)
        self.assertAlmostEqual(threshold, 0.40)
        metrics = evaluate_scores(y, scores, threshold)
        self.assertAlmostEqual(metrics["pr_auc"], average_precision_score(y, scores))
        self.assertEqual(metrics["confusion_matrix"], [[2, 1], [0, 3]])
        self.assertEqual(metrics["false_negatives"], 0)


class AI4IIntegrationTests(unittest.TestCase):
    def test_complete_run_produces_consistent_artifacts(self):
        from src.ai4i.workflow import run_experiment

        with tempfile.TemporaryDirectory() as temporary:
            outputs = run_experiment(ROOT, Path(temporary), quick=True)
            target = Path(temporary)
            metrics = json.loads((target / "metrics.json").read_text(encoding="utf-8"))
            audit = json.loads((target / "data_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["rows"], 10000)
            self.assertEqual(sum(sum(row) for row in metrics["confusion_matrix"]), metrics["test_samples"])
            self.assertEqual(metrics["false_negatives"], metrics["confusion_matrix"][1][0])
            self.assertEqual(outputs["selected_model"], metrics["selected_model"])
            self.assertTrue((target / "eda" / "pca.png").stat().st_size > 1000)
            self.assertTrue((target / "figures" / "precision_recall.png").stat().st_size > 1000)
            self.assertTrue((target / "figures" / "validation_threshold_tradeoff.png").stat().st_size > 1000)
            self.assertTrue((target / "figures" / "model_comparison.png").stat().st_size > 1000)
            baseline = json.loads((target / "baseline_test_metrics.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(baseline["pr_auc"], metrics["positive_samples"] / metrics["test_samples"])


if __name__ == "__main__":
    unittest.main()
