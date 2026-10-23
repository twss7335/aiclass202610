from pathlib import Path

from src.iris_workflow import run_experiment


if __name__ == "__main__":
    metrics = run_experiment(Path(__file__).resolve().parent)
    print("Experiment complete")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print(f"PCA variance (3 PCs): {metrics['pca_explained_variance_total']:.4f}")
