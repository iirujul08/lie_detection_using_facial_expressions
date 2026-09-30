import os
import json
from pathlib import Path
import pandas as pd
import numpy as np

from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
import joblib


# ============================================================
# CONFIG
# ============================================================

DATASET_FILE = Path("dataset_features.csv")
MODEL_OUTPUT_PATH = Path("backend/app/trained_model.joblib")
WEIGHTS_OUTPUT_PATH = Path("backend/app/au_weights.json")

AU_COLUMNS = [
    "AU01", "AU02", "AU04", "AU05", "AU06", "AU07",
    "AU09", "AU10", "AU11", "AU12", "AU14", "AU15",
    "AU17", "AU20", "AU23", "AU24", "AU25", "AU26",
    "AU28", "AU43",
]


def load_dataset():
    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"Feature dataset file '{DATASET_FILE}' not found. "
            f"Run 'extract_dataset_features.py' first to extract Action Unit features."
        )

    df = pd.read_csv(DATASET_FILE)
    print(f"Loaded {len(df)} samples from {DATASET_FILE}")
    print("\nClass distribution:")
    print(df["label"].value_counts().rename(index={0: "Truthful (0)", 1: "Deceptive (1)"}))

    missing_cols = [col for col in AU_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Dataset missing required AU columns: {missing_cols}")

    X = df[AU_COLUMNS].values
    y = df["label"].values.astype(int)

    return df, X, y


def train_and_evaluate(X, y):
    print("\n" + "=" * 60)
    print("TRAINING MACHINE LEARNING MODELS")
    print("=" * 60)

    unique_classes, counts = np.unique(y, return_counts=True)
    min_class_count = int(np.min(counts)) if len(counts) > 0 else 0
    n_samples = len(y)

    pipelines = {
        "RandomForest": Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5))
        ]),
        "GradientBoosting": Pipeline([
            ("scaler", StandardScaler()),
            ("gb", GradientBoostingClassifier(n_estimators=100, random_state=42, learning_rate=0.05, max_depth=3))
        ]),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(random_state=42, C=1.0))
        ]),
        "SVM (RBF)": Pipeline([
            ("scaler", StandardScaler()),
            ("svm", SVC(probability=True, random_state=42, C=1.0))
        ]),
        "MLPClassifier": Pipeline([
            ("scaler", StandardScaler()),
            ("mlp", MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=500, random_state=42))
        ]),
    }

    # If dataset has fewer than 2 classes or min class count < 2 (e.g. initial extraction checkpoint)
    if len(unique_classes) < 2 or min_class_count < 2:
        print(
            f"\nNOTE: Dataset currently contains {n_samples} sample(s) across {len(unique_classes)} class(es)."
        )
        print("Feature extraction is still in progress on the full video dataset.")
        print("Fitting default model directly on available extracted samples...")

        best_model_name = "RandomForest"
        best_pipeline = pipelines[best_model_name]
        
        # Fit on available data
        if len(unique_classes) == 1:
            # Create a simple dummy 2-class setup for initial weights if only 1 class extracted so far
            X_fit = np.vstack([X, X + 0.01])
            y_fit = np.array([y[0]] * len(y) + [1 - y[0]] * len(y))
            best_pipeline.fit(X_fit, y_fit)
        else:
            best_pipeline.fit(X, y)

        results_df = pd.DataFrame([{"Model": best_model_name, "Samples": n_samples, "Status": "Fitted on available checkpoint"}])
        return best_model_name, best_pipeline, results_df

    n_splits = min(5, min_class_count)
    print(f"Running {n_splits}-Fold Stratified Cross-Validation across models...")

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    scoring = ["accuracy", "precision", "recall", "f1"]
    if len(unique_classes) == 2:
        scoring.append("roc_auc")

    model_results = {}

    for name, pipeline in pipelines.items():
        try:
            scores = cross_validate(pipeline, X, y, cv=cv, scoring=scoring)
            res = {
                "Accuracy": np.mean(scores["test_accuracy"]),
                "Precision": np.mean(scores["test_precision"]),
                "Recall": np.mean(scores["test_recall"]),
                "F1": np.mean(scores["test_f1"]),
                "pipeline": pipeline
            }
            if "test_roc_auc" in scores:
                res["ROC_AUC"] = np.mean(scores["test_roc_auc"])
            model_results[name] = res
        except Exception as e:
            print(f"  Warning: {name} cross-validation skipped: {e}")

    if not model_results:
        best_model_name = "RandomForest"
        best_pipeline = pipelines[best_model_name]
        best_pipeline.fit(X, y)
        results_df = pd.DataFrame([{"Model": best_model_name, "Samples": n_samples, "Status": "Direct Fit"}])
        return best_model_name, best_pipeline, results_df

    results_df = pd.DataFrame(model_results).T.drop(columns=["pipeline"])
    print("\nCross-Validation Performance Summary:")
    print(results_df.round(4))

    score_col = "ROC_AUC" if "ROC_AUC" in results_df.columns else "Accuracy"
    best_model_name = results_df[score_col].astype(float).idxmax()
    print(f"\n[BEST] Top Performing Model: {best_model_name}")

    best_pipeline = pipelines[best_model_name]
    best_pipeline.fit(X, y)

    return best_model_name, best_pipeline, results_df



def extract_au_importance(best_model_name, best_pipeline):
    classifier = best_pipeline.named_steps[list(best_pipeline.named_steps.keys())[-1]]
    
    if hasattr(classifier, "feature_importances_"):
        importances = classifier.feature_importances_
    elif hasattr(classifier, "coef_"):
        importances = np.abs(classifier.coef_[0])
    else:
        # Uniform fallback for models without explicit feature importances
        importances = np.ones(len(AU_COLUMNS)) / len(AU_COLUMNS)

    # Normalize weights to sum to 1.0
    importances = importances / np.sum(importances)

    importance_dict = {
        au: float(imp) for au, imp in zip(AU_COLUMNS, importances)
    }

    # Sort descending
    sorted_importances = dict(
        sorted(importance_dict.items(), key=lambda item: item[1], reverse=True)
    )

    print("\nAction Unit Feature Importance Ranking:")
    for au, imp in sorted_importances.items():
        bar = "#" * int(imp * 50)
        print(f"  {au}: {imp:.4f} {bar}")

    return sorted_importances, importances


def save_artifacts(best_model_name, best_pipeline, au_importances):
    MODEL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(best_pipeline, MODEL_OUTPUT_PATH)
    print(f"\n[OK] Saved trained pipeline model to: {MODEL_OUTPUT_PATH.resolve()}")

    weights_payload = {
        "model_name": best_model_name,
        "n_features": len(AU_COLUMNS),
        "au_columns": AU_COLUMNS,
        "au_importances": au_importances,
    }

    with open(WEIGHTS_OUTPUT_PATH, "w") as f:
        json.dump(weights_payload, f, indent=2)

    print(f"[OK] Saved AU feature weights to: {WEIGHTS_OUTPUT_PATH.resolve()}")


def main():
    print("=" * 60)
    print("AI LIE DETECTOR - ML MODEL TRAINING")
    print("=" * 60)

    try:
        df, X, y = load_dataset()
    except FileNotFoundError as e:
        print(f"\n{e}")
        return

    best_name, best_pipeline, results_df = train_and_evaluate(X, y)
    sorted_importances, importance_vec = extract_au_importance(best_name, best_pipeline)
    save_artifacts(best_name, best_pipeline, sorted_importances)

    print("\n" + "=" * 60)
    print("TRAINING & EXPORT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
