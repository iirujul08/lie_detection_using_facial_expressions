"""
ML + Personal Baseline Deception Scoring Engine.

Combines:
1. ML Model Inference: Calculates deception_probability using trained sklearn pipeline.
2. Personal Baseline Calibration: Measures facial Action Unit drift (baseline_deviation) relative to session baseline profile.
3. Hybrid Risk Synthesis: Combines ML probability (60% weight) and personal baseline deviation (40% weight) into risk_score (0-100%).

IMPORTANT:
This metric is a statistical signal drift indicator and risk estimate, NOT proof of lying.
"""

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

from .feature_extraction import AU_COLUMNS


# ============================================================
# PATHS & CONSTANTS
# ============================================================

MODEL_FILE = Path(__file__).parent / "trained_model.joblib"

DEFAULT_DISCLAIMER = (
    "DISCLAIMER: Risk score is an ML biometric micro-expression drift estimate "
    "relative to your personal baseline. It is not proof of lying or deception."
)

_model = None


def get_model():
    global _model

    if _model is None:
        if not MODEL_FILE.exists():
            raise FileNotFoundError(
                f"Trained model not found: {MODEL_FILE}"
            )

        _model = joblib.load(MODEL_FILE)

    return _model


# ============================================================
# BASELINE PROFILE
# ============================================================

@dataclass
class BaselineProfile:
    mean: np.ndarray
    std: np.ndarray
    n_samples: int

    def flag_low_confidence_inputs(
        self,
        min_samples: int = 3
    ) -> list[str]:

        warnings = []

        if self.n_samples < min_samples:
            warnings.append(
                f"Only {self.n_samples} baseline sample(s) collected; "
                f"recommend at least {min_samples} for a stable baseline profile."
            )

        return warnings


def build_baseline_profile(
    baseline_vectors: list[np.ndarray]
) -> BaselineProfile:

    if not baseline_vectors:
        raise ValueError(
            "Need at least one baseline sample to build a profile."
        )

    stacked = np.stack(
        baseline_vectors,
        axis=0
    )

    std = stacked.std(axis=0)
    # Prevent division by zero when calculating Z-scores
    std = np.where(std == 0, 1e-4, std)

    return BaselineProfile(
        mean=stacked.mean(axis=0),
        std=std,
        n_samples=stacked.shape[0],
    )


# ============================================================
# DISTANCE METRICS
# ============================================================

def _cosine_distance(
    a: np.ndarray,
    b: np.ndarray
) -> float:

    denom = (
        np.linalg.norm(a)
        * np.linalg.norm(b)
    )

    if denom == 0:
        return 0.0

    cosine_similarity = np.dot(a, b) / denom
    return float(np.clip(1.0 - cosine_similarity, 0.0, 1.0))


# ============================================================
# ML PREDICTION
# ============================================================

def score_with_model(
    question_vector: np.ndarray
) -> float:

    model = get_model()

    features = np.asarray(
        question_vector,
        dtype=np.float64
    ).reshape(1, -1)

    if features.shape[1] != len(AU_COLUMNS):
        raise ValueError(
            f"Expected {len(AU_COLUMNS)} AU features, "
            f"received {features.shape[1]}."
        )

    probabilities = model.predict_proba(features)[0]
    classes = list(model.classes_)

    if 1 in classes:
        deceptive_index = classes.index(1)
        return float(probabilities[deceptive_index])

    return 0.0


# ============================================================
# FINAL SCORING FUNCTION
# ============================================================

def score_against_baseline(
    question_vector: np.ndarray,
    profile: BaselineProfile,
) -> dict:

    question_vector = np.asarray(
        question_vector,
        dtype=np.float64
    )

    # 1. ML Model Probability
    deception_probability = score_with_model(question_vector)

    # 2. Personal Baseline Deviation
    raw_cosine = _cosine_distance(question_vector, profile.mean)
    z_diff = np.abs(question_vector - profile.mean) / profile.std
    mean_z_drift = float(np.mean(z_diff))

    # Scale deviation metrics to normalized [0.0, 1.0] range
    scaled_cosine = min(1.0, raw_cosine * 3.5)
    scaled_z = min(1.0, mean_z_drift / 2.0)
    baseline_deviation = round(float(0.5 * scaled_cosine + 0.5 * scaled_z), 4)

    # 3. Hybrid Deception Risk Score (0 - 100)
    # 60% weight on trained ML model + 40% weight on personal baseline drift
    composite_risk = (0.60 * deception_probability) + (0.40 * baseline_deviation)
    risk_score = round(float(np.clip(composite_risk * 100.0, 0.0, 100.0)), 1)

    # Risk level categorization
    if risk_score < 35.0:
        risk_level = "Low"
    elif risk_score < 65.0:
        risk_level = "Medium"
    else:
        risk_level = "High"

    # 4. Warnings & Disclaimer
    warnings = profile.flag_low_confidence_inputs()
    warnings.append(
        "Risk score synthesizes trained ML model probabilities with personal facial AU drift."
    )

    return {
        "deception_probability": round(deception_probability, 4),
        "baseline_deviation": baseline_deviation,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "meter": risk_score,
        "bucket": risk_level,
        "warnings": warnings,
        "disclaimer": DEFAULT_DISCLAIMER,
    }