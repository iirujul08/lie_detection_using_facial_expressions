"""
Turns AU vectors into a presentable "lie potential" score.

Two things live here on purpose, kept separate:
1. build_baseline_profile() -- combines multiple baseline-question AU vectors into
   one reference profile (mean + std) for a person. Using several samples, not one,
   is the mitigation for a faked/atypical single baseline answer (see doubt log).
2. score_against_baseline() -- compares a real-question AU vector to that profile.

AU_WEIGHTS is a placeholder (uniform) until a model is trained on labeled
deceptive/truthful clips to learn which AUs are actually informative. Swap
load_weights() to read a trained weight vector once that model exists -- nothing
else in this file needs to change.
"""

from dataclasses import dataclass
import numpy as np

N_AUS = 20  # must match len(AU_COLUMNS) in feature_extraction.py

# Placeholder: uniform weighting. Replace with trained per-AU importance weights.
AU_WEIGHTS = np.ones(N_AUS, dtype=np.float64) / N_AUS


@dataclass
class BaselineProfile:
    mean: np.ndarray
    std: np.ndarray
    n_samples: int

    def flag_low_confidence_inputs(self, min_samples: int = 3) -> list[str]:
        warnings = []
        if self.n_samples < min_samples:
            warnings.append(
                f"Only {self.n_samples} baseline sample(s) collected; "
                f"recommend at least {min_samples} for a stable baseline."
            )
        return warnings


def build_baseline_profile(baseline_vectors: list[np.ndarray]) -> BaselineProfile:
    if not baseline_vectors:
        raise ValueError("Need at least one baseline sample to build a profile.")
    stacked = np.stack(baseline_vectors, axis=0)
    return BaselineProfile(
        mean=stacked.mean(axis=0),
        std=stacked.std(axis=0),
        n_samples=stacked.shape[0],
    )


def _weighted_cosine_distance(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> float:
    """Cosine distance on weighted AU vectors. Chosen over Euclidean because it's
    more robust to overall intensity/lighting differences between clips -- see
    feature extraction design notes."""
    aw, bw = a * weights, b * weights
    denom = np.linalg.norm(aw) * np.linalg.norm(bw)
    if denom == 0:
        return 0.0
    cosine_sim = np.dot(aw, bw) / denom
    return 1.0 - cosine_sim


def score_against_baseline(
    question_vector: np.ndarray,
    profile: BaselineProfile,
    weights: np.ndarray = AU_WEIGHTS,
) -> dict:
    raw_distance = _weighted_cosine_distance(question_vector, profile.mean, weights)

    # Normalize into a 0-100 "lie potential" meter. This threshold-based bucketing
    # is a placeholder scale -- calibrate against real session data once you have
    # some, rather than treating 0.15/0.35 as ground truth.
    meter = float(np.clip(raw_distance / 0.5, 0.0, 1.0) * 100)
    if raw_distance < 0.15:
        bucket = "Low"
    elif raw_distance < 0.35:
        bucket = "Medium"
    else:
        bucket = "High"

    return {
        "raw_distance": raw_distance,
        "meter": round(meter, 1),
        "bucket": bucket,
        "warnings": profile.flag_low_confidence_inputs(),
    }
