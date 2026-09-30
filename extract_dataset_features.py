import sys
import os
import tempfile
import shutil
from pathlib import Path
import cv2
import pandas as pd
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


# ============================================================
# CONFIG
# ============================================================

DATASET_ROOT = Path("RealLifeDeceptionDetection.2016")
OUTPUT_FILE = Path("dataset_features.csv")

AU_COLUMNS = [
    "AU01", "AU02", "AU04", "AU05", "AU06", "AU07",
    "AU09", "AU10", "AU11", "AU12", "AU14", "AU15",
    "AU17", "AU20", "AU23", "AU24", "AU25", "AU26",
    "AU28", "AU43",
]

VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
}

# Take one frame every N frames
FRAME_STEP = 15
MAX_FRAMES_PER_VIDEO = 20
MAX_IMAGE_WIDTH = 640


# ============================================================
# FIND CLIPS
# ============================================================

def find_clips_directory():
    matches = list(DATASET_ROOT.rglob("Clips"))
    if not matches:
        raise FileNotFoundError(
            f"Could not find the Clips folder under {DATASET_ROOT}."
        )
    return matches[0]


# ============================================================
# FIND VIDEOS
# ============================================================

def find_videos(clips_dir):
    videos = []
    for path in clips_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        parts = {p.name.lower() for p in path.parents}
        if "deceptive" in parts:
            label = 1
        elif "truthful" in parts:
            label = 0
        else:
            continue
        videos.append((path, label))
    return sorted(videos, key=lambda x: x[0].name)


# ============================================================
# EXTRACT SAMPLED FRAMES TO TEMP DIRECTORY
# ============================================================

def extract_sampled_frames(video_path, tmp_dir):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  WARNING: Could not open video {video_path}")
        return []

    img_paths = []
    frame_number = 0

    while True:
        success, frame = cap.read()
        if not success:
            break

        if frame_number % FRAME_STEP == 0:
            h, w = frame.shape[:2]
            if w > MAX_IMAGE_WIDTH:
                new_h = int(h * (MAX_IMAGE_WIDTH / w))
                frame = cv2.resize(frame, (MAX_IMAGE_WIDTH, new_h))
            
            p = os.path.join(tmp_dir, f"frame_{frame_number:05d}.jpg")
            cv2.imwrite(p, frame)
            img_paths.append(p)

            if len(img_paths) >= MAX_FRAMES_PER_VIDEO:
                break

        frame_number += 1

    cap.release()
    return img_paths


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("REAL-LIFE DECEPTION DATASET")
    print("AU FEATURE EXTRACTION PIPELINE")
    print("=" * 60)

    clips_dir = find_clips_directory()
    print(f"\nClips directory found: {clips_dir}")

    videos = find_videos(clips_dir)
    print(f"Total videos identified: {len(videos)}")

    deceptive = sum(label == 1 for _, label in videos)
    truthful = sum(label == 0 for _, label in videos)
    print(f"  Truthful : {truthful}")
    print(f"  Deceptive: {deceptive}")

    # Check for existing progress to enable resume
    processed_videos = set()
    existing_rows = []
    if OUTPUT_FILE.exists():
        try:
            prev_df = pd.read_csv(OUTPUT_FILE)
            if "video" in prev_df.columns:
                processed_videos = set(prev_df["video"].astype(str))
                existing_rows = prev_df.to_dict(orient="records")
                print(f"\nResuming feature extraction: {len(processed_videos)} videos already processed.")
        except Exception as e:
            print(f"\nCould not load existing {OUTPUT_FILE}: {e}")

    print("\nLoading Py-Feat AU Detector...")
    detector = Detector(
        face_model="retinaface",
        landmark_model="mobilefacenet",
        au_model="xgb",
        emotion_model=None,
    )
    print("Py-Feat Detector successfully loaded.")

    rows = list(existing_rows)

    for index, (video_path, label) in enumerate(videos, start=1):
        video_str = str(video_path)
        if video_str in processed_videos:
            continue

        label_name = "DECEPTIVE" if label == 1 else "TRUTHFUL"
        print(f"\n[{index}/{len(videos)}] Processing: {video_path.name} ({label_name})")

        tmp_dir = tempfile.mkdtemp()
        try:
            img_paths = extract_sampled_frames(video_path, tmp_dir)
            if not img_paths:
                print("  WARNING: No frames extracted from clip.")
                shutil.rmtree(tmp_dir)
                continue

            # Run Py-Feat AU detector across sampled frames in batch
            results = detector.detect(
                img_paths,
                data_type="image",
                batch_size=len(img_paths),
                progress_bar=False,
            )

            available_aus = [col for col in AU_COLUMNS if col in results.columns]
            if not available_aus:
                print("  WARNING: AU columns missing in detector output.")
                shutil.rmtree(tmp_dir)
                continue

            au_df = results[available_aus]
            # Filter out frames with no valid AU detections
            au_df = au_df.dropna(how="all")

            if au_df.empty:
                print("  WARNING: No valid face/AU detected in extracted frames.")
                shutil.rmtree(tmp_dir)
                continue

            mean_aus = au_df.mean(axis=0)

            row = {
                "video": video_str,
                "video_name": video_path.name,
                "label": label,
                "frames_analyzed": len(au_df),
            }

            for au in AU_COLUMNS:
                row[au] = float(mean_aus.get(au, 0.0))

            rows.append(row)
            processed_videos.add(video_str)

            # Checkpoint progress to CSV after each video
            df_checkpoint = pd.DataFrame(rows)
            df_checkpoint.to_csv(OUTPUT_FILE, index=False)
            print(f"  ✓ Extracted AUs from {len(au_df)} frames. Saved checkpoint to {OUTPUT_FILE}")

        except Exception as e:
            print(f"  ERROR processing {video_path.name}: {e}")
        finally:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)

    if not rows:
        raise RuntimeError("No videos were successfully processed.")

    df_final = pd.DataFrame(rows)
    df_final.to_csv(OUTPUT_FILE, index=False)

    print("\n" + "=" * 60)
    print("FEATURE EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"\nFinal dataset saved to: {OUTPUT_FILE.resolve()}")
    print(f"Total video samples extracted: {len(df_final)}")
    print("\nLabel Distribution:")
    print(df_final["label"].value_counts())
    print(f"\nFeature Columns ({len(AU_COLUMNS)} Action Units):")
    print(AU_COLUMNS)


if __name__ == "__main__":
    main()
