import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from iris_workflow import (  # noqa: E402
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_model,
    explore_data,
    load_iris_csv,
    split_data,
)


class IrisWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_path = ROOT / "data" / "iris.csv"
        cls.frame = load_iris_csv(cls.data_path)

    def test_dataset_has_expected_schema_and_balanced_classes(self):
        self.assertEqual(self.frame.shape, (150, 5))
        self.assertEqual(list(self.frame.columns), [*FEATURE_COLUMNS, TARGET_COLUMN])
        self.assertEqual(self.frame[TARGET_COLUMN].value_counts().to_dict(), {
            "Iris-setosa": 50,
            "Iris-versicolor": 50,
            "Iris-virginica": 50,
        })

    def test_dataset_has_no_missing_values_and_known_duplicate_count(self):
        report = explore_data(self.frame)
        self.assertEqual(report["missing_values_total"], 0)
        self.assertEqual(report["duplicate_rows"], 1)
        self.assertEqual(report["rows"], 150)
        self.assertEqual(report["feature_count"], 4)

    def test_split_is_stratified_and_reproducible(self):
        first = split_data(self.frame, test_size=0.2, random_state=42)
        second = split_data(self.frame, test_size=0.2, random_state=42)
        X_train, X_test, y_train, y_test = first
        self.assertEqual((len(X_train), len(X_test)), (120, 30))
        self.assertEqual(y_train.value_counts().to_dict(), {
            "Iris-setosa": 40,
            "Iris-versicolor": 40,
            "Iris-virginica": 40,
        })
        self.assertTrue(y_test.equals(second[3]))
        self.assertTrue(X_test.equals(second[1]))

    def test_model_pipeline_prevents_preprocessing_leakage(self):
        model = build_model(random_state=42)
        self.assertEqual(list(model.named_steps), ["scaler", "classifier"])
        self.assertEqual(model.named_steps["classifier"].hidden_layer_sizes, (16, 8))


class GeneratedArtifactTests(unittest.TestCase):
    def test_metrics_contract_after_analysis_run(self):
        metrics_path = ROOT / "results" / "metrics.json"
        if not metrics_path.exists():
            self.skipTest("analysis has not generated metrics yet")
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(metrics["accuracy"], 0.85)
        self.assertEqual(len(metrics["confusion_matrix"]), 3)
        self.assertAlmostEqual(sum(metrics["pca_explained_variance_ratio"]), metrics["pca_explained_variance_total"])


if __name__ == "__main__":
    unittest.main()
