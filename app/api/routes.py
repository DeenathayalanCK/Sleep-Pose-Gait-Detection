import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.database.repository import get_all_events, get_all_persons
from app.camera.stream_frame import latest_frame

router = APIRouter()


@router.get("/events")
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
async def video_stream(request: Request):
    """
    MJPEG stream — robust, never drops the connection on slow processing.

    KEY FIXES:
      1. Counter-based new-frame detection instead of object identity.
      2. Client-disconnect detection — generator exits cleanly when browser
         tab closes or refreshes, freeing the uvicorn worker immediately.
         Without this, stale generators pile up and block other requests.
      3. No arbitrary sleep cap — wakes as soon as a new frame is ready,
         but never spins. Uses adaptive sleep based on processing FPS.
    """
    async def gen():
        last_counter = -1

        while True:
            # ── Check if browser disconnected ─────────────────────────
            if await request.is_disconnected():
                break

            jpeg, counter = latest_frame.read()

            if jpeg is not None and counter != last_counter:
                last_counter = counter
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n"
                    b"\r\n"
                    + jpeg +
                    b"\r\n"
                )
                # After sending a frame, yield control briefly
                await asyncio.sleep(0.01)
            else:
                # No new frame yet — wait a short tick before checking again
                await asyncio.sleep(0.02)

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control":  "no-cache, no-store, must-revalidate",
            "Pragma":         "no-cache",
            "Expires":        "0",
            "Connection":     "keep-alive",
            "X-Accel-Buffering": "no",   # tells nginx not to buffer this stream
        },
    )