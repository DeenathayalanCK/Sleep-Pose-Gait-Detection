import os
from dotenv import load_dotenv

load_dotenv()

VIDEO_SOURCE = os.getenv("VIDEO_SOURCE")

EAR_THRESHOLD = float(os.getenv("EAR_THRESHOLD"))
FATIGUE_SECONDS = int(os.getenv("FATIGUE_SECONDS"))

FRAME_WIDTH = int(os.getenv("FRAME_WIDTH"))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT"))

DATABASE_PATH = os.getenv("DATABASE_PATH")
SNAPSHOT_DIR = os.getenv("SNAPSHOT_DIR")

OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")