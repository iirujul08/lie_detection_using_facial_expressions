"""
Extracts facial Action Unit (AU) intensity vectors from a video clip using py-feat.

Design note: we return ONE averaged AU vector per clip (per question / per baseline
sample), not a per-frame time series. Averaging across frames smooths out blinks,
brief head turns, and single-frame detection noise -- see project doubt log re:
expressionless subjects needing a stable per-person reference rather than a
frame-by-frame threshold.
"""

import sys
import os
import tempfile
import shutil
import cv2
import numpy as np
from unittest.mock import MagicMock

# Guard torchcodec on Windows where DLLs may be missing
if 'torchcodec' not in sys.modules:
    try:
        import torchcodec  # noqa: F401
    except Exception:
        sys.modules['torchcodec'] = MagicMock()
        sys.modules['torchcodec.decoders'] = MagicMock()

try:
    from feat import Detector
except ImportError:
    from feat.detector import Detectorv1 as Detector

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
            emotion_model=None,
        )
    return _detector


def extract_au_vector(video_path: str, sample_every_n_frames: int = 15, max_frames: int = 20) -> np.ndarray:
    """
    Run AU detection across a video clip and return a single averaged AU vector.

    Frames where no face is detected are dropped rather than zero-filled, so a
    brief look-away doesn't drag the average toward zero across every AU.
    """
    detector = get_detector()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file at {video_path}")

    tmp_dir = tempfile.mkdtemp()
    img_paths = []
    frame_number = 0

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            if frame_number % sample_every_n_frames == 0:
                h, w = frame.shape[:2]
                if w > 640:
                    new_h = int(h * (640 / w))
                    frame = cv2.resize(frame, (640, new_h))
                
                p = os.path.join(tmp_dir, f"frame_{frame_number:05d}.jpg")
                cv2.imwrite(p, frame)
                img_paths.append(p)

                if len(img_paths) >= max_frames:
                    break

            frame_number += 1
    finally:
        cap.release()

    if not img_paths:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        raise ValueError("No frames extracted from the uploaded video clip.")

    try:
        result = detector.detect(img_paths, data_type="image", batch_size=len(img_paths), progress_bar=False)
        au_frame = result[AU_COLUMNS].dropna(how="all")
        if au_frame.empty:
            raise ValueError(
                "No face detected in any sampled frame of this clip. "
                "Ask the user to retake the clip with better lighting/framing."
            )
        return au_frame.mean(axis=0).to_numpy(dtype=np.float64)
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

