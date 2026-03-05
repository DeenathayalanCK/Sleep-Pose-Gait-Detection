import os
from dotenv import load_dotenv

load_dotenv()

def _float(key, default): return float(os.getenv(key, default))
def _int(key, default):   return int(os.getenv(key, default))
def _str(key, default):   return os.getenv(key, default)

# ── Camera / video ─────────────────────────────────────────────────────────────
VIDEO_SOURCE  = _str("VIDEO_SOURCE", "data/videos/test.mp4")
CAMERA_ID     = _str("CAMERA_ID",    "camera_1")
FRAME_WIDTH   = _int("FRAME_WIDTH",  "640")
FRAME_HEIGHT  = _int("FRAME_HEIGHT", "480")

# ── Storage ────────────────────────────────────────────────────────────────────
DATABASE_PATH = _str("DATABASE_PATH", "data/database/events.db")
SNAPSHOT_DIR  = _str("SNAPSHOT_DIR",  "data/snapshots")

# ── LLM ───────────────────────────────────────────────────────────────────────
OLLAMA_HOST  = _str("OLLAMA_HOST",  "http://localhost:11434")
OLLAMA_MODEL = _str("OLLAMA_MODEL", "llama3:8b")

# ── Eye / EAR (secondary signal — only when frontal face visible) ──────────────
EAR_THRESHOLD = _float("EAR_THRESHOLD", "0.25")

# ── Sleep / inactivity thresholds ─────────────────────────────────────────────
# How many seconds of zero motion before declaring SLEEPING.
# Primary signal — works for ANY posture (reclined, head-on-desk, slumped).
SLEEP_SECONDS  = _float("SLEEP_SECONDS",  "10.0")

# How many seconds of low motion before declaring DROWSY.
DROWSY_SECONDS = _float("DROWSY_SECONDS", "5.0")

# If reclined AND inactive >= this (shorter) time → also sleeping.
# Lets the system react faster when body posture is clearly reclined.
SLEEP_SECONDS_RECLINED = _float("SLEEP_SECONDS_RECLINED", "7.0")

# Recline ratio at which the body is considered "clearly reclined" (0–1).
# 0.60 = body X-span is 60% of total span — works for chair-reclined posture.
# Raise if false positives; lower if reclined posture misses.
RECLINE_THRESHOLD = _float("RECLINE_THRESHOLD", "0.60")

# Recline ratio below which recline signal is ignored entirely.
RECLINE_MIN = _float("RECLINE_MIN", "0.50")

# ── Motion sensitivity ─────────────────────────────────────────────────────────
# Mean per-pixel intensity change below which frame is considered "no motion".
# Lower = more sensitive (picks up tiny movements).
# Raise for busy/noisy backgrounds; lower for static scenes.
MOTION_THRESHOLD = _float("MOTION_THRESHOLD", "1.2")

# ── Alert cooldown ─────────────────────────────────────────────────────────────
# Seconds to wait before re-alerting for the same continuous sleep episode.
ALERT_COOLDOWN_SECONDS = _float("ALERT_COOLDOWN_SECONDS", "30.0")

# ── MediaPipe pose confidence ──────────────────────────────────────────────────
# Lower for distant/angled cameras; raise for close/frontal cameras.
POSE_DETECTION_CONFIDENCE  = _float("POSE_DETECTION_CONFIDENCE",  "0.45")
POSE_TRACKING_CONFIDENCE   = _float("POSE_TRACKING_CONFIDENCE",   "0.45")
POSE_LANDMARK_MIN_VISIBILITY = _float("POSE_LANDMARK_MIN_VISIBILITY", "0.35")

# ── Smoothing ──────────────────────────────────────────────────────────────────
# Number of frames to average recline ratio over (reduces flicker).
RECLINE_SMOOTH_FRAMES = _int("RECLINE_SMOOTH_FRAMES", "8")

# ── Multi-person tracking (YOLO + ByteTrack) ───────────────────────────────────
# Max persons to run full MediaPipe skeleton on per frame.
# Sorted by bounding-box area (largest = nearest). Rest get bbox+state only.
MAX_POSE_PERSONS = _int("MAX_POSE_PERSONS", "6")

# Seconds a track can be absent before its state/history is discarded.
TRACK_TIMEOUT_SECONDS = _float("TRACK_TIMEOUT_SECONDS", "30.0")

# Seconds to remember a person's cumulative session for re-entry matching.
TRACK_REENTRY_SECONDS = _float("TRACK_REENTRY_SECONDS", "120.0")

# YOLO model — yolov8n.pt (nano, CPU-friendly) downloads automatically.
# Override with yolov8s.pt / yolov8m.pt for better accuracy at cost of speed.
YOLO_MODEL       = _str("YOLO_MODEL",       "yolov8n.pt")
YOLO_CONF        = _float("YOLO_CONF",       "0.35")
YOLO_IOU         = _float("YOLO_IOU",        "0.45")

# Posture thresholds (all camera-agnostic ratios)
POSTURE_WALK_MOTION_THRESHOLD = _float("POSTURE_WALK_MOTION_THRESHOLD", "5.0")
POSTURE_SIT_Y_RATIO           = _float("POSTURE_SIT_Y_RATIO",           "0.20")
POSTURE_STAND_Y_RATIO         = _float("POSTURE_STAND_Y_RATIO",         "0.12")