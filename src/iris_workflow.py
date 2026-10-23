"""Reproducible Iris exploration, PCA, and neural-network workflow."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


FEATURE_COLUMNS = [
    "sepal_length_cm",
    "sepal_width_cm",
    "petal_length_cm",
    "petal_width_cm",
]
TARGET_COLUMN = "species"
CLASS_ORDER = ["Iris-setosa", "Iris-versicolor", "Iris-virginica"]


def load_iris_csv(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    expected = [*FEATURE_COLUMNS, TARGET_COLUMN]
    if list(frame.columns) != expected:
        raise ValueError(f"Expected columns {expected}, got {list(frame.columns)}")
    return frame


def explore_data(frame: pd.DataFrame) -> dict:
    return {
        "rows": int(len(frame)),
        "columns": int(frame.shape[1]),
        "feature_count": len(FEATURE_COLUMNS),
        "missing_values_total": int(frame.isna().sum().sum()),
        "missing_values_by_column": {
            key: int(value) for key, value in frame.isna().sum().items()
        },
        "duplicate_rows": int(frame.duplicated().sum()),
        "class_distribution": {
            key: int(value)
            for key, value in frame[TARGET_COLUMN].value_counts().sort_index().items()
        },
        "data_types": {key: str(value) for key, value in frame.dtypes.items()},
        "descriptive_statistics": frame[FEATURE_COLUMNS].describe().round(4).to_dict(),
    }


def split_data(frame: pd.DataFrame, test_size: float = 0.2, random_state: int = 42):
    X = frame[FEATURE_COLUMNS]
    y = frame[TARGET_COLUMN]
    return train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )


def build_model(random_state: int = 42) -> Pipeline:
    classifier = MLPClassifier(
        hidden_layer_sizes=(16, 8),
        activation="relu",
        solver="adam",
        alpha=0.001,
        batch_size=16,
        learning_rate_init=0.01,
        max_iter=1000,
        early_stopping=True,
        validation_fraction=0.2,
        n_iter_no_change=40,
        random_state=random_state,
    )
    return Pipeline([("scaler", StandardScaler()), ("classifier", classifier)])


def _save_eda_plots(frame: pd.DataFrame, figure_dir: Path) -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    pair = sns.pairplot(
        frame,
        vars=FEATURE_COLUMNS,
        hue=TARGET_COLUMN,
        hue_order=CLASS_ORDER,
        corner=True,
        diag_kind="hist",
        plot_kws={"alpha": 0.75, "s": 32},
    )
    pair.fig.suptitle("Iris feature distributions and relationships", y=1.02)
    pair.savefig(figure_dir / "eda_pairplot.png", dpi=180, bbox_inches="tight")
    plt.close(pair.fig)

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        frame[FEATURE_COLUMNS].corr(),
        annot=True,
        fmt=".2f",
        cmap="vlag",
        center=0,
        square=True,
        ax=ax,
    )
    ax.set_title("Feature correlation matrix")
    fig.tight_layout()
    fig.savefig(figure_dir / "feature_correlation.png", dpi=180)
    plt.close(fig)


def _run_pca(frame: pd.DataFrame, figure_dir: Path) -> tuple[list[float], float]:
    scaled = StandardScaler().fit_transform(frame[FEATURE_COLUMNS])
    pca = PCA(n_components=3)
    components = pca.fit_transform(scaled)
    ratios = pca.explained_variance_ratio_

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    colors = ["#0072B2", "#E69F00", "#009E73"]
    for species, color in zip(CLASS_ORDER, colors):
        mask = frame[TARGET_COLUMN].eq(species).to_numpy()
        ax.scatter(
            components[mask, 0],
            components[mask, 1],
            components[mask, 2],
            label=species.replace("Iris-", ""),
            color=color,
            s=48,
            alpha=0.8,
            edgecolor="white",
            linewidth=0.4,
        )
    ax.set_xlabel(f"PC1 ({ratios[0]:.1%})")
    ax.set_ylabel(f"PC2 ({ratios[1]:.1%})")
    ax.set_zlabel(f"PC3 ({ratios[2]:.1%})")
    ax.set_title("3D PCA projection of standardized Iris features")
    ax.legend(title="Species")
    fig.tight_layout()
    fig.savefig(figure_dir / "pca_3d.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return [float(value) for value in ratios], float(ratios.sum())


def _save_training_plot(classifier: MLPClassifier, figure_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    epochs = np.arange(1, len(classifier.loss_curve_) + 1)
    axes[0].plot(epochs, classifier.loss_curve_, color="#0072B2", linewidth=2)
    axes[0].set(title="Training loss", xlabel="Epoch", ylabel="Log loss")
    axes[0].grid(alpha=0.25)

    validation_scores = classifier.validation_scores_ or []
    validation_epochs = np.arange(1, len(validation_scores) + 1)
    axes[1].plot(validation_epochs, validation_scores, color="#009E73", linewidth=2)
    axes[1].set(
        title="Validation accuracy (early stopping)",
        xlabel="Epoch",
        ylabel="Accuracy",
        ylim=(0, 1.05),
    )
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_dir / "training_history.png", dpi=180)
    plt.close(fig)


def _save_confusion_matrix(matrix: np.ndarray, figure_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=[name.replace("Iris-", "") for name in CLASS_ORDER],
        yticklabels=[name.replace("Iris-", "") for name in CLASS_ORDER],
        cbar=False,
        ax=ax,
    )
    ax.set(title="Test-set confusion matrix", xlabel="Predicted", ylabel="Actual")
    fig.tight_layout()
    fig.savefig(figure_dir / "confusion_matrix.png", dpi=180)
    plt.close(fig)


def run_experiment(project_root: str | Path) -> dict:
    root = Path(project_root)
    result_dir = root / "results"
    figure_dir = result_dir / "figures"
    result_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    frame = load_iris_csv(root / "data" / "iris.csv")
    exploration = explore_data(frame)
    (result_dir / "exploration.json").write_text(
        json.dumps(exploration, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    frame[FEATURE_COLUMNS].describe().round(4).to_csv(result_dir / "descriptive_statistics.csv")
    _save_eda_plots(frame, figure_dir)
    pca_ratios, pca_total = _run_pca(frame, figure_dir)

    X_train, X_test, y_train_names, y_test_names = split_data(frame)
    class_to_id = {name: index for index, name in enumerate(CLASS_ORDER)}
    y_train = y_train_names.map(class_to_id)
    y_test = y_test_names.map(class_to_id)
    model = build_model()
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    class_ids = list(range(len(CLASS_ORDER)))
    matrix = confusion_matrix(y_test, predictions, labels=class_ids)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, predictions, average="macro", zero_division=0
    )
    report = classification_report(
        y_test,
        predictions,
        labels=class_ids,
        target_names=CLASS_ORDER,
        digits=4,
        zero_division=0,
    )
    classifier = model.named_steps["classifier"]
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "macro_precision": float(precision),
        "macro_recall": float(recall),
        "macro_f1": float(f1),
        "confusion_matrix": matrix.tolist(),
        "class_order": CLASS_ORDER,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "test_size": 0.2,
        "random_state": 42,
        "stratified": True,
        "epochs_run": int(classifier.n_iter_),
        "best_validation_accuracy": float(classifier.best_validation_score_),
        "pca_explained_variance_ratio": pca_ratios,
        "pca_explained_variance_total": pca_total,
    }
    (result_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (result_dir / "classification_report.txt").write_text(report, encoding="utf-8")
    _save_training_plot(classifier, figure_dir)
    _save_confusion_matrix(matrix, figure_dir)
    return metrics

