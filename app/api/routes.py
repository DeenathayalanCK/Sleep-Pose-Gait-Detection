import asyncio
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.database.repository import get_all_events
from app.camera.stream_frame import latest_frame

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/events")
def get_events():
    return [e.to_dict() for e in get_all_events()]


@router.get("/status")
def get_status():
    from app.main import current_status
    return current_status


@router.get("/stream")
async def video_stream():
    """
    MJPEG stream endpoint.
    The browser <img src="/stream"> connects once and receives a continuous
    multipart/x-mixed-replace stream of JPEG frames.
    """
    async def frame_generator():
        while True:
            jpeg = latest_frame.read()
            if jpeg:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + jpeg +
                    b"\r\n"
                )
            await asyncio.sleep(0.04)   # ~25 fps cap

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"},
    )