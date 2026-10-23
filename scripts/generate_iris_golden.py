"""Generate fixed Iris predictions from the Python model for JS parity tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.iris_workflow import (
    CLASS_ORDER,
    FEATURE_COLUMNS,
    build_model,
    load_iris_csv,
    split_data,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tests" / "golden.json"

FIXED_INPUTS = [
    {
        "name": "setosa_reference",
        "values": {
            "sepal_length_cm": 5.1,
            "sepal_width_cm": 3.5,
            "petal_length_cm": 1.4,
            "petal_width_cm": 0.2,
        },
    },
    {
        "name": "versicolor_reference",
        "values": {
            "sepal_length_cm": 6.0,
            "sepal_width_cm": 2.9,
            "petal_length_cm": 4.5,
            "petal_width_cm": 1.5,
        },
    },
    {
        "name": "virginica_reference",
        "values": {
            "sepal_length_cm": 6.5,
            "sepal_width_cm": 3.0,
            "petal_length_cm": 5.8,
            "petal_width_cm": 2.2,
        },
    },
]


def generate() -> dict:
    frame = load_iris_csv(ROOT / "data" / "iris.csv")
    X_train, _, y_train, _ = split_data(frame)
    class_ids = {name: index for index, name in enumerate(CLASS_ORDER)}
    model = build_model()
    model.fit(X_train, y_train.map(class_ids))

    inputs = pd.DataFrame(
        [case["values"] for case in FIXED_INPUTS],
        columns=FEATURE_COLUMNS,
    )
    probabilities = model.predict_proba(inputs)
    predictions = np.argmax(probabilities, axis=1)
    return {
        "model": "iris",
        "source": "src/iris_workflow.py:build_model",
        "random_state": 42,
        "feature_order": FEATURE_COLUMNS,
        "class_order": CLASS_ORDER,
        "cases": [
            {
                "name": case["name"],
                "input": case["values"],
                "expected_class": CLASS_ORDER[int(prediction)],
                "probabilities": [float(value) for value in row],
            }
            for case, prediction, row in zip(FIXED_INPUTS, predictions, probabilities)
        ],
    }


def main() -> None:
    OUTPUT.write_text(
        json.dumps(generate(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(FIXED_INPUTS)} Python predictions to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
