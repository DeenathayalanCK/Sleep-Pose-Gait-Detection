import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import SNAPSHOT_DIR


def create_app() -> FastAPI:
    app = FastAPI(title="Sleep & Fatigue Detection API", version="1.0.0")

    # Allow all origins — covers Docker bridge IPs and any frontend host
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # /health — was 404 because it was defined on a different app instance
    # in main.py after create_app() had already returned
    @app.get("/health")
    def health():
        return {"status": "running", "service": "fatigue-detection-ai"}

    # Register API routes (/events, etc.)
    app.include_router(router)

    # Serve snapshot images so frontend <img> tags resolve correctly
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    app.mount("/snapshots", StaticFiles(directory=SNAPSHOT_DIR), name="snapshots")

    return app