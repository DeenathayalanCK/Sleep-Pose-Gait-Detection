import os
from dotenv import load_dotenv

load_dotenv()


def _get(key, default=None, cast=str):
    val = os.getenv(key, default)
    if val is None:
        raise EnvironmentError(f"Required env variable '{key}' is not set.")
    return cast(val)


# Camera / video
VIDEO_SOURCE     = os.getenv("VIDEO_SOURCE", "data/videos/test.mp4")
CAMERA_ID        = os.getenv("CAMERA_ID", "camera_1")

# Detection thresholds
# BUG FIX: original code did float(os.getenv(...)) with no default — crashes
# with TypeError when variable is missing from .env
EAR_THRESHOLD    = float(os.getenv("EAR_THRESHOLD", "0.25"))
FATIGUE_SECONDS  = int(os.getenv("FATIGUE_SECONDS", "5"))

# Frame dimensions
FRAME_WIDTH      = int(os.getenv("FRAME_WIDTH", "640"))
FRAME_HEIGHT     = int(os.getenv("FRAME_HEIGHT", "480"))

# Storage
DATABASE_PATH    = os.getenv("DATABASE_PATH", "data/database/events.db")
SNAPSHOT_DIR     = os.getenv("SNAPSHOT_DIR", "data/snapshots")

# LLM (optional — features degrade gracefully if not set)
OLLAMA_HOST      = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "llama3:8b")
