"""
Extracts facial Action Unit (AU) intensity vectors from a video clip using py-feat.

Design note: we return ONE averaged AU vector per clip (per question / per baseline
sample), not a per-frame time series. Averaging across frames smooths out blinks,
brief head turns, and single-frame detection noise -- see project doubt log re:
expressionless subjects needing a stable per-person reference rather than a
frame-by-frame threshold.
"""

import numpy as np
from feat import Detector

# AU columns py-feat's default model outputs. Keep this list explicit (rather than
# reading it off the Detector at runtime) so the vector's dimension and ordering are
# stable across sessions -- the deviation scorer assumes a fixed-order vector.
AU_COLUMNS = [
    "AU01", "AU02", "AU04", "AU05", "AU06", "AU07", "AU09", "AU10",
    "AU11", "AU12", "AU14", "AU15", "AU17", "AU20", "AU23", "AU24",
    "AU25", "AU26", "AU28", "AU43",
]

_detector = None


def get_detector() -> Detector:
    """Lazily construct the py-feat Detector (loads model weights on first call)."""
    global _detector
    if _detector is None:
        _detector = Detector(
            face_model="retinaface",
            landmark_model="mobilefacenet",
            au_model="xgb",
            emotion_model=None,   # not needed for this pipeline, skip to save time
            facepose_model=None,
        )
    return _detector


def extract_au_vector(video_path: str, sample_every_n_frames: int = 3) -> np.ndarray:
    """
    Run AU detection across a video clip and return a single averaged AU vector.

    Frames where no face is detected are dropped rather than zero-filled, so a
    brief look-away doesn't drag the average toward zero across every AU.
    """
    detector = get_detector()
    result = detector.detect_video(video_path, skip_frames=sample_every_n_frames)

    au_frame = result[AU_COLUMNS].dropna(how="all")
    if au_frame.empty:
        raise ValueError(
            "No face detected in any sampled frame of this clip. "
            "Ask the user to retake the clip with better lighting/framing."
        )

    return au_frame.mean(axis=0).to_numpy(dtype=np.float64)
