"""Rebuild all AI4I 2020 outputs from the stored UCI CSV."""

from pathlib import Path

from src.ai4i.workflow import run_experiment


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    result = run_experiment(root, root / "results" / "ai4i")
    print(f"Selected: {result['selected_model']} / {result['selected_features']}")
    print(f"Test AP: {result['pr_auc']:.4f}; recall: {result['recall']:.4f}; precision: {result['precision']:.4f}")
