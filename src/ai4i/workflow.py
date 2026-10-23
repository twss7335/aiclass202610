"""Offline, testable AI4I 2020 analysis and binary classification workflow."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn import __version__ as sklearn_version
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


FEATURE_COLUMNS = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]
NUMERIC_COLUMNS = FEATURE_COLUMNS[1:]
FAILURE_MODES = ["TWF", "HDF", "PWF", "OSF", "RNF"]
TARGET = "Machine failure"
EXPECTED_COLUMNS = ["UDI", "Product ID", *FEATURE_COLUMNS, TARGET, *FAILURE_MODES]
DERIVED_COLUMNS = ["temperature_difference_K", "power_W", "wear_torque_minNm"]
SEED = 42


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def load_data(path: Path | str) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if list(frame.columns) != EXPECTED_COLUMNS:
        raise ValueError(f"Unexpected AI4I columns: {list(frame.columns)}")
    if frame[TARGET].isna().any() or not set(frame[TARGET].unique()).issubset({0, 1}):
        raise ValueError("Machine failure must contain only 0 and 1")
    for mode in FAILURE_MODES:
        if frame[mode].isna().any() or not set(frame[mode].unique()).issubset({0, 1}):
            raise ValueError(f"{mode} must contain only 0 and 1")
    return frame


def audit_data(frame: pd.DataFrame) -> dict:
    modes = frame[FAILURE_MODES].astype(int)
    any_mode = modes.any(axis=1)
    combinations = modes.apply(
        lambda row: "+".join(mode for mode in FAILURE_MODES if row[mode]) or "none",
        axis=1,
    )
    ranges = {
        name: {"min": float(frame[name].min()), "max": float(frame[name].max()),
               "mean": float(frame[name].mean())}
        for name in NUMERIC_COLUMNS
    }
    return {
        "rows": int(len(frame)),
        "columns": int(frame.shape[1]),
        "column_types": {name: str(dtype) for name, dtype in frame.dtypes.items()},
        "missing_total": int(frame.isna().sum().sum()),
        "missing_by_column": {name: int(count) for name, count in frame.isna().sum().items()},
        "duplicate_full_rows": int(frame.duplicated().sum()),
        "duplicate_measurements": int(frame[[*FEATURE_COLUMNS, TARGET, *FAILURE_MODES]].duplicated().sum()),
        "class_counts": {str(label): int(count) for label, count in frame[TARGET].value_counts().sort_index().items()},
        "failure_rate": float(frame[TARGET].mean()),
        "type_counts": {name: int(count) for name, count in frame["Type"].value_counts().sort_index().items()},
        "mode_counts": {name: int(modes[name].sum()) for name in FAILURE_MODES},
        "mode_combinations": dict(sorted(Counter(combinations).items())),
        "multiple_modes": int((modes.sum(axis=1) > 1).sum()),
        "failure_without_mode": int(((frame[TARGET] == 1) & ~any_mode).sum()),
        "mode_without_failure": int(((frame[TARGET] == 0) & any_mode).sum()),
        "numeric_ranges": ranges,
    }


def engineer_features(features: pd.DataFrame) -> pd.DataFrame:
    result = features[FEATURE_COLUMNS].copy()
    result["temperature_difference_K"] = result["Process temperature [K]"] - result["Air temperature [K]"]
    result["power_W"] = result["Torque [Nm]"] * result["Rotational speed [rpm]"] * (2 * np.pi / 60)
    result["wear_torque_minNm"] = result["Tool wear [min]"] * result["Torque [Nm]"]
    return result


def make_split(frame: pd.DataFrame, seed: int = SEED) -> tuple[np.ndarray, np.ndarray]:
    positions = np.arange(len(frame))
    return train_test_split(positions, test_size=0.2, random_state=seed, stratify=frame[TARGET])


def balanced_weights(y: np.ndarray | pd.Series) -> dict[int, float]:
    labels, counts = np.unique(np.asarray(y), return_counts=True)
    if len(labels) < 2:
        raise ValueError("Both classes are required in a training fold")
    return {int(label): float(len(y) / (len(labels) * count)) for label, count in zip(labels, counts)}


def pca_projection(frame: pd.DataFrame) -> tuple[np.ndarray, list[float]]:
    values = StandardScaler().fit_transform(frame[NUMERIC_COLUMNS])
    pca = PCA(n_components=2, random_state=SEED)
    points = pca.fit_transform(values)
    return points, [float(v) for v in pca.explained_variance_ratio_]


def _plot_eda(frame: pd.DataFrame, out: Path, audit: dict) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    counts = frame[TARGET].value_counts().reindex([0, 1], fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(["Normal", "Failure"], counts, color=["#4778A8", "#D55E00"])
    for i, value in enumerate(counts):
        ax.text(i, value, f"{value:,} ({value / len(frame):.1%})", ha="center", va="bottom")
    ax.set(title=f"AI4I class balance (n={len(frame):,})", ylabel="Observations")
    fig.tight_layout()
    fig.savefig(out / "class_balance.png", dpi=160)
    plt.close(fig)

    by_type = frame.groupby("Type")[TARGET].agg(["sum", "count", "mean"])
    by_type.rename(columns={"sum": "failures", "count": "observations", "mean": "failure_rate"}).to_csv(out / "type_failure_rates.csv")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(by_type.index, by_type["mean"], color="#4778A8")
    ax.set(title="Failure rate by product type", xlabel="Type", ylabel="Failure rate", ylim=(0, max(0.06, by_type["mean"].max() * 1.2)))
    fig.tight_layout()
    fig.savefig(out / "type_failure_rates.png", dpi=160)
    plt.close(fig)

    frame.groupby(TARGET)[NUMERIC_COLUMNS].agg(["mean", "std", "median"]).to_csv(out / "feature_summary.csv")
    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    for ax, name in zip(axes.flat, NUMERIC_COLUMNS):
        for label, color in [(0, "#4778A8"), (1, "#D55E00")]:
            ax.hist(frame.loc[frame[TARGET] == label, name], bins=30, density=True, alpha=.45,
                    label="Failure" if label else "Normal", color=color)
        ax.set_title(name, fontsize=9)
    axes[0, 0].legend()
    fig.suptitle("Numeric features by machine-failure status (density)")
    fig.tight_layout()
    fig.savefig(out / "feature_distributions.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 6))
    corr = frame[NUMERIC_COLUMNS].corr().to_numpy()
    image = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(NUMERIC_COLUMNS)), NUMERIC_COLUMNS, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(NUMERIC_COLUMNS)), NUMERIC_COLUMNS, fontsize=8)
    fig.colorbar(image, ax=ax, label="Pearson r")
    ax.set_title("Numeric-feature correlation")
    fig.tight_layout()
    fig.savefig(out / "correlation.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(FAILURE_MODES, [audit["mode_counts"][mode] for mode in FAILURE_MODES], color="#8E65A8")
    ax.set(title="Failure-mode label counts (overlap possible)", ylabel="Observations")
    fig.tight_layout()
    fig.savefig(out / "failure_modes.png", dpi=160)
    plt.close(fig)

    points, ratio = pca_projection(frame)
    fig, ax = plt.subplots(figsize=(8, 6))
    for label, color, title in [(0, "#4778A8", "Normal"), (1, "#D55E00", "Failure")]:
        mask = frame[TARGET].to_numpy() == label
        ax.scatter(points[mask, 0], points[mask, 1], s=13 if label == 0 else 23,
                   alpha=.23 if label == 0 else .8, color=color, label=f"{title} (n={mask.sum():,})")
    ax.set(xlabel=f"PC1 ({ratio[0]:.1%})", ylabel=f"PC2 ({ratio[1]:.1%})",
           title="PCA of standardized numeric operating features")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "pca.png", dpi=170)
    plt.close(fig)
    info = {"input_features": NUMERIC_COLUMNS, "explained_variance_ratio": ratio,
            "cumulative_variance_ratio": float(sum(ratio)), "purpose": "descriptive only"}
    _write_json(out / "pca.json", info)
    return info


def _features(frame: pd.DataFrame, variant: str) -> pd.DataFrame:
    base = frame[FEATURE_COLUMNS]
    if variant == "raw":
        return base.copy()
    if variant == "engineered":
        return engineer_features(base)
    raise ValueError(variant)


def _pipeline(model_name: str, variant: str, seed: int, weights: dict[int, float]) -> Pipeline:
    numeric = NUMERIC_COLUMNS + (DERIVED_COLUMNS if variant == "engineered" else [])
    preprocessor = ColumnTransformer([
        ("numeric", StandardScaler(), numeric),
        ("type", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["Type"]),
    ])
    if model_name == "dummy":
        estimator = DummyClassifier(strategy="prior")
    elif model_name == "logistic":
        estimator = LogisticRegression(max_iter=500, class_weight=weights, random_state=seed)
    elif model_name == "forest":
        estimator = RandomForestClassifier(n_estimators=120, min_samples_leaf=2, n_jobs=1,
                                           class_weight=weights, random_state=seed)
    elif model_name == "mlp":
        estimator = MLPClassifier(hidden_layer_sizes=(24, 12), activation="relu", solver="adam",
                                  alpha=.01, batch_size=128, learning_rate_init=.003,
                                  max_iter=180, early_stopping=False, random_state=seed)
    else:
        raise ValueError(model_name)
    return Pipeline([("preprocess", preprocessor), ("model", estimator)])


def _fit_model(model: Pipeline, model_name: str, X: pd.DataFrame, y: np.ndarray, weights: dict[int, float]) -> Pipeline:
    if model_name == "mlp":
        sample_weights = np.asarray([weights[int(label)] for label in y])
        model.fit(X, y, model__sample_weight=sample_weights)
    else:
        model.fit(X, y)
    return model


def choose_threshold(y_validation: np.ndarray, validation_scores: np.ndarray,
                     target_recall: float = .90) -> float:
    """Maximize precision among validation thresholds meeting the recall target."""
    y = np.asarray(y_validation, dtype=int)
    scores = np.asarray(validation_scores, dtype=float)
    if len(y) != len(scores) or not (0 < target_recall <= 1) or len(np.unique(y)) != 2:
        raise ValueError("Invalid validation labels, scores, or recall target")
    candidates = np.unique(scores)
    feasible = []
    for threshold in candidates:
        predictions = scores >= threshold
        recall = recall_score(y, predictions, zero_division=0)
        if recall >= target_recall:
            precision = precision_score(y, predictions, zero_division=0)
            feasible.append((precision, float(threshold)))
    return max(feasible)[1]


def evaluate_scores(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    y = np.asarray(y_true, dtype=int)
    probabilities = np.asarray(scores, dtype=float)
    predicted = (probabilities >= threshold).astype(int)
    matrix = confusion_matrix(y, predicted, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    return {
        "pr_auc": float(average_precision_score(y, probabilities)),
        "roc_auc": float(roc_auc_score(y, probabilities)) if len(np.unique(y)) == 2 else None,
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "threshold": float(threshold),
        "confusion_matrix": matrix.tolist(),
        "true_negatives": int(tn), "false_positives": int(fp),
        "false_negatives": int(fn), "true_positives": int(tp),
        "predicted_inspections": int(fp + tp),
        "positive_samples": int((y == 1).sum()),
        "negative_samples": int((y == 0).sum()),
    }


def _cross_validate(X: pd.DataFrame, y: np.ndarray, model_name: str, variant: str,
                    seed: int, folds: int) -> tuple[dict, np.ndarray]:
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    out_of_fold = np.full(len(y), np.nan)
    fold_scores = []
    for fold, (fit_idx, validation_idx) in enumerate(splitter.split(X, y)):
        weights = balanced_weights(y[fit_idx])
        model = _pipeline(model_name, variant, seed + fold, weights)
        _fit_model(model, model_name, X.iloc[fit_idx], y[fit_idx], weights)
        scores = model.predict_proba(X.iloc[validation_idx])[:, 1]
        out_of_fold[validation_idx] = scores
        fold_scores.append(float(average_precision_score(y[validation_idx], scores)))
    return {
        "model": model_name, "features": variant,
        "pr_auc_mean": float(np.mean(fold_scores)), "pr_auc_std": float(np.std(fold_scores)),
        "pr_auc_oof": float(average_precision_score(y, out_of_fold)),
        "fold_pr_auc": fold_scores,
        "weighting": "none (prior baseline)" if model_name == "dummy" else
                     ("fold-local class_weight" if model_name != "mlp" else "fold-local class_weight mapped to sample_weight"),
    }, out_of_fold


def _plot_evaluation(y: np.ndarray, scores: np.ndarray, threshold: float,
                     metrics: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    precision, recall, _ = precision_recall_curve(y, scores)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(recall, precision, color="#D55E00", label=f"AP={metrics['pr_auc']:.3f}")
    ax.axhline(y.mean(), linestyle="--", color="gray", label=f"Prevalence={y.mean():.3f}")
    ax.set(xlabel="Failure recall", ylabel="Failure precision", title="Independent-test precision–recall curve", xlim=(0, 1), ylim=(0, 1))
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "precision_recall.png", dpi=170)
    plt.close(fig)

    fpr, tpr, _ = roc_curve(y, scores)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(fpr, tpr, color="#4778A8", label=f"AUC={metrics['roc_auc']:.3f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
    ax.set(xlabel="False-positive rate", ylabel="Failure recall", title="Independent-test ROC curve", xlim=(0, 1), ylim=(0, 1))
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "roc.png", dpi=170)
    plt.close(fig)

    matrix = np.asarray(metrics["confusion_matrix"])
    fig, ax = plt.subplots(figsize=(6, 5))
    image = ax.imshow(matrix, cmap="Blues")
    for row in range(2):
        for col in range(2):
            ax.text(col, row, str(matrix[row, col]), ha="center", va="center", fontsize=15)
    ax.set_xticks([0, 1], ["Normal", "Failure"])
    ax.set_yticks([0, 1], ["Normal", "Failure"])
    ax.set(xlabel="Predicted", ylabel="Actual", title=f"Test confusion matrix (threshold={threshold:.3f})")
    fig.colorbar(image, ax=ax)
    fig.tight_layout()
    fig.savefig(out / "confusion_matrix.png", dpi=170)
    plt.close(fig)

    _plot_threshold_tradeoff(y, scores, threshold, out.parent / "threshold_tradeoff_test.csv",
                             out / "threshold_tradeoff.png", "Test-set threshold sensitivity (descriptive only)")


def _plot_threshold_tradeoff(y: np.ndarray, scores: np.ndarray, threshold: float,
                             csv_path: Path, figure_path: Path, title: str) -> None:
    thresholds = np.unique(np.r_[np.linspace(0, 1, 101), threshold])
    rows = []
    for candidate in thresholds:
        predicted = scores >= candidate
        rows.append({"threshold": float(candidate),
                     "precision": float(precision_score(y, predicted, zero_division=0)),
                     "recall": float(recall_score(y, predicted, zero_division=0)),
                     "false_positives": int(((y == 0) & predicted).sum()),
                     "false_negatives": int(((y == 1) & ~predicted).sum()),
                     "inspections": int(predicted.sum())})
    tradeoff = pd.DataFrame(rows)
    tradeoff.to_csv(csv_path, index=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].plot(tradeoff.threshold, tradeoff.precision, label="Precision")
    axes[0].plot(tradeoff.threshold, tradeoff.recall, label="Recall")
    axes[0].set(ylabel="Score", xlabel="Threshold", ylim=(0, 1.05))
    axes[0].legend()
    axes[1].plot(tradeoff.threshold, tradeoff.false_positives, label="False alarms")
    axes[1].plot(tradeoff.threshold, tradeoff.false_negatives, label="Missed failures")
    axes[1].plot(tradeoff.threshold, tradeoff.inspections, label="Inspections", alpha=.7)
    axes[1].set(ylabel="Observations", xlabel="Threshold")
    axes[1].legend()
    for ax in axes:
        ax.axvline(threshold, color="black", linestyle="--", alpha=.7)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(figure_path, dpi=170)
    plt.close(fig)


def run_experiment(project_root: Path | str, output_dir: Path | str,
                   quick: bool = False) -> dict:
    root, out = Path(project_root), Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data_path = root / "data" / "ai4i" / "ai4i2020.csv"
    frame = load_data(data_path)
    audit = audit_data(frame)
    audit["file_sha256"] = hashlib.sha256(data_path.read_bytes()).hexdigest()
    _write_json(out / "data_audit.json", audit)
    pca = _plot_eda(frame, out / "eda", audit)

    train_idx, test_idx = make_split(frame)
    train = frame.iloc[train_idx]
    test = frame.iloc[test_idx]
    train_y = train[TARGET].to_numpy()
    test_y = test[TARGET].to_numpy()
    _write_json(out / "split_config.json", {
        "seed": SEED, "test_fraction": .2, "stratified": True,
        "train_samples": len(train), "test_samples": len(test),
        "train_failures": int(train_y.sum()), "test_failures": int(test_y.sum()),
        "cv_folds": 2 if quick else 3,
        "feature_whitelist": FEATURE_COLUMNS,
        "excluded_identifiers": ["UDI", "Product ID"],
        "excluded_target_labels": [TARGET, *FAILURE_MODES],
    })

    rows = []
    oof_by_candidate = {}
    for variant in ["raw", "engineered"]:
        X = _features(train, variant)
        for name in ["dummy", "logistic", "forest", "mlp"]:
            row, scores = _cross_validate(X, train_y, name, variant, SEED, 2 if quick else 3)
            rows.append(row)
            oof_by_candidate[(variant, name)] = scores
    comparison = pd.DataFrame([{k: v for k, v in row.items() if k != "fold_pr_auc"} for row in rows])
    comparison.sort_values("pr_auc_mean", ascending=False).to_csv(out / "model_comparison.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    ordered = comparison.sort_values("pr_auc_mean")
    ax.barh(ordered["model"] + " / " + ordered["features"], ordered["pr_auc_mean"],
            xerr=ordered["pr_auc_std"], color="#4778A8", alpha=.9)
    ax.set(xlabel="Mean validation PR-AUC (Average Precision)", title="Stratified cross-validation model comparison", xlim=(0, 1))
    fig.tight_layout()
    (out / "figures").mkdir(exist_ok=True)
    fig.savefig(out / "figures" / "model_comparison.png", dpi=170)
    plt.close(fig)
    ranking = sorted(rows, key=lambda row: (row["pr_auc_mean"], row["pr_auc_oof"]), reverse=True)
    selected = ranking[0]
    variant, model_name = selected["features"], selected["model"]
    oof = oof_by_candidate[(variant, model_name)]
    pd.DataFrame({"train_position": train_idx, "label": train_y, "oof_failure_score": oof}).to_csv(out / "validation_scores.csv", index=False)
    threshold = choose_threshold(train_y, oof)
    _plot_threshold_tradeoff(train_y, oof, threshold, out / "threshold_tradeoff_validation.csv",
                             out / "figures" / "validation_threshold_tradeoff.png",
                             "Out-of-fold validation: threshold chosen here")

    X_train, X_test = _features(train, variant), _features(test, variant)
    weights = balanced_weights(train_y)
    model = _fit_model(_pipeline(model_name, variant, SEED, weights), model_name, X_train, train_y, weights)
    scores = model.predict_proba(X_test)[:, 1]
    metrics = evaluate_scores(test_y, scores, threshold)
    metrics.update({"selected_model": model_name, "selected_features": variant,
                    "selection_cv_pr_auc_mean": selected["pr_auc_mean"],
                    "selection_cv_pr_auc_std": selected["pr_auc_std"],
                    "validation_target_recall": .9,
                    "threshold_selection": "maximize precision among OOF thresholds with recall >= 0.90",
                    "train_samples": len(train), "test_samples": len(test),
                    "weighting": selected["weighting"]})
    _write_json(out / "metrics.json", metrics)
    baseline_scores = np.full(len(test_y), float(train_y.mean()))
    baseline_metrics = evaluate_scores(test_y, baseline_scores, threshold)
    baseline_metrics["method"] = "training-prevalence prior"
    _write_json(out / "baseline_test_metrics.json", baseline_metrics)
    pd.DataFrame({"UDI": test["UDI"].to_numpy(), "actual": test_y, "score": scores,
                  "predicted": (scores >= threshold).astype(int)}).to_csv(out / "test_predictions.csv", index=False)
    mistakes = pd.DataFrame({"UDI": test["UDI"].to_numpy(), "actual": test_y, "score": scores,
                             "predicted": (scores >= threshold).astype(int)})
    mistakes[mistakes.actual != mistakes.predicted].to_csv(out / "error_cases.csv", index=False)
    _plot_evaluation(test_y, scores, threshold, metrics, out / "figures")

    if model_name != "dummy":
        importance = permutation_importance(model, X_test, test_y, scoring="average_precision",
                                            n_repeats=3, random_state=SEED, n_jobs=1)
        pd.DataFrame({"feature": X_test.columns, "ap_drop_mean": importance.importances_mean,
                      "ap_drop_std": importance.importances_std}).sort_values("ap_drop_mean", ascending=False).to_csv(
                          out / "feature_importance.csv", index=False)

    chronological = frame.sort_values("UDI", kind="stable")
    split_at = int(len(chronological) * .8)
    sequence_train, sequence_test = chronological.iloc[:split_at], chronological.iloc[split_at:]
    sequence_y = sequence_train[TARGET].to_numpy()
    sequence_weights = balanced_weights(sequence_y)
    sequence_model = _fit_model(_pipeline(model_name, variant, SEED, sequence_weights), model_name,
                                _features(sequence_train, variant), sequence_y, sequence_weights)
    sequence_scores = sequence_model.predict_proba(_features(sequence_test, variant))[:, 1]
    sequence_metrics = evaluate_scores(sequence_test[TARGET].to_numpy(), sequence_scores, threshold)
    sequence_metrics["interpretation"] = "Row-order sensitivity, not a validated forecast horizon; threshold carried over from random-split training validation."
    _write_json(out / "sequence_sensitivity.json", sequence_metrics)

    config = {"seed": SEED, "scikit_learn": sklearn_version, "models": ["dummy", "logistic", "forest", "mlp"],
              "feature_variants": ["raw", "engineered"], "cv_folds": 2 if quick else 3,
              "selected_model": model_name, "selected_features": variant,
              "mlp": {"hidden_layers": [24, 12], "activation": "relu", "solver": "adam", "alpha": .01,
                      "batch_size": 128, "learning_rate_init": .003, "max_iter": 180},
              "class_imbalance": "class weights only; no resampling", "pca": pca}
    _write_json(out / "experiment_config.json", config)
    return metrics
