import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.api.calibration import cal_router
from app.config import SNAPSHOT_DIR

# Always absolute — same as snapshot_service
_ABS_SNAPSHOT_DIR = os.path.abspath(SNAPSHOT_DIR)


def create_app() -> FastAPI:
    app = FastAPI(title="Sleep & Fatigue Detection API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "running", "service": "fatigue-detection-ai"}

    app.include_router(router)
    app.include_router(cal_router)

    os.makedirs(_ABS_SNAPSHOT_DIR, exist_ok=True)
    app.mount("/snapshots", StaticFiles(directory=_ABS_SNAPSHOT_DIR), name="snapshots")

    return app