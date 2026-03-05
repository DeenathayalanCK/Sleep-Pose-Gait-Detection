import time
import datetime
import logging
from threading import Thread

from app.config import ALERT_COOLDOWN_SECONDS, CAMERA_ID
from app.detection.sleep_pose_detector import SleepAnalysis

logger = logging.getLogger(__name__)


class FatigueEngine:
    """
    Tracks sleep episodes with start/end times and full metrics.

    On episode START  → immediately writes a DB record + saves snapshot.
                        LLM summary runs in background thread so it never
                        blocks or loses the event.
    On episode END    → updates the record with ended_at + final duration.
    Cooldown          → prevents re-alerting during the same episode.
    """

    def __init__(self):
        self._sleep_start:    float | None = None
        self._sleep_start_dt: str | None   = None
        self._last_alert_at:  float | None = None
        self._current_event_id: int | None = None

    def update(self, analysis: SleepAnalysis,
               snapshot_frame=None) -> tuple[bool, float]:
        """
        Returns (new_alert_fired, duration_seconds).
        Pass snapshot_frame (BGR ndarray) to capture keyframe on detection.
        """
        from app.services.snapshot_service import save_snapshot
        from app.database.repository import insert_event, update_event_end
        from app.llm.event_summarizer import summarize

        now    = time.monotonic()
        now_dt = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")

        if analysis.state == "sleeping":
            # ── Episode start ─────────────────────────────────────────────
            if self._sleep_start is None:
                self._sleep_start    = now
                self._sleep_start_dt = now_dt
                logger.info("Sleep episode started")

            duration = now - self._sleep_start

            in_cooldown = (
                self._last_alert_at is not None
                and (now - self._last_alert_at) < ALERT_COOLDOWN_SECONDS
            )

            if not in_cooldown:
                self._last_alert_at = now

                # Save snapshot immediately — don't wait for LLM
                snapshot_path = (
                    save_snapshot(snapshot_frame)
                    if snapshot_frame is not None else None
                )

                # Write DB record immediately
                event = insert_event(
                    camera_id        = CAMERA_ID,
                    started_at       = self._sleep_start_dt,
                    ended_at         = None,
                    duration         = round(duration, 1),
                    trigger          = analysis.debug.get("trigger", "unknown"),
                    reclined_ratio   = analysis.reclined_ratio,
                    inactive_seconds = analysis.inactive_seconds,
                    confidence       = analysis.confidence,
                    snapshot         = snapshot_path,
                    summary          = None,   # filled async below
                )

                if event:
                    self._current_event_id = event.id
                    logger.warning(
                        f"SLEEP EVENT #{event.id} | "
                        f"trigger={analysis.debug.get('trigger')} | "
                        f"inactive={analysis.inactive_seconds:.0f}s | "
                        f"recline={analysis.reclined_ratio:.2f}"
                    )
                    # LLM summary in background — won't block or lose the event
                    eid = event.id
                    dur = round(duration, 1)
                    Thread(
                        target=self._summarise_async,
                        args=(eid, dur),
                        daemon=True,
                    ).start()

                return True, round(duration, 1)

        else:
            # ── Episode end ───────────────────────────────────────────────
            if self._sleep_start is not None:
                total = now - self._sleep_start
                logger.info(f"Sleep episode ended after {total:.1f}s")

                if self._current_event_id is not None:
                    Thread(
                        target=update_event_end,
                        args=(self._current_event_id, now_dt,
                              round(total, 1), None),
                        daemon=True,
                    ).start()

            self._sleep_start      = None
            self._sleep_start_dt   = None
            self._current_event_id = None

        return False, 0.0

    @staticmethod
    def _summarise_async(event_id: int, duration: float):
        from app.llm.event_summarizer import summarize
        from app.database.repository import update_event_end
        try:
            summary = summarize(duration)
            # patch summary only — don't overwrite ended_at
            from app.database.db import SessionLocal
            from app.database.models import SleepEvent
            db = SessionLocal()
            try:
                ev = db.query(SleepEvent).filter(SleepEvent.id == event_id).first()
                if ev:
                    ev.summary = summary
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Async summarise failed: {e}")