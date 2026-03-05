import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.database.repository import get_all_events, get_all_persons
from app.camera.stream_frame import latest_frame

router = APIRouter()


@router.get("/events")          # kept for backward compat
@router.get("/fatigue-events")
def get_fatigue_events():
    return [e.to_dict() for e in get_all_events()]


@router.get("/persons")
def get_persons():
    return [p.to_dict() for p in get_all_persons()]


@router.get("/status")
def get_status():
    from app.main import current_persons
    return current_persons


@router.get("/stream")
async def video_stream():
    async def gen():
        while True:
            jpeg = latest_frame.read()
            if jpeg:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                       + jpeg + b"\r\n")
            await asyncio.sleep(0.04)
    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"},
    )