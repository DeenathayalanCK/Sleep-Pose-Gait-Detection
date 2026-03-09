import time
import datetime
import logging
from threading import Thread

from app.config import ALERT_COOLDOWN_SECONDS, CAMERA_ID
from app.detection.sleep_pose_detector import SleepAnalysis
from app.detection.risk_scorer import compute_risk

logger = logging.getLogger(__name__)


def _build_cause(state: str, analysis: SleepAnalysis) -> str:
    """
    Build a plain-English explanation of WHY this fatigue record was created.
    Includes EAR/PERCLOS when available.
    """
    inactive = analysis.inactive_seconds
    recline  = analysis.reclined_ratio
    trigger  = analysis.debug.get("trigger", "")
    sigs     = analysis.signals or {}
    perclos  = sigs.get("perclos")
    head_drop= sigs.get("head_drop_angle")

    if state == "sleeping":
        if trigger == "perclos" and perclos is not None:
            return (f"Eyes closed {perclos:.0%} of last 60 frames (PERCLOS) "
                    f"— direct physiological sleep signal")
        elif trigger == "inactivity":
            return (f"No movement for {inactive:.0f}s "
                    f"(recline={recline:.0%})")
        elif trigger == "head_drop" and head_drop:
            return (f"Head drooped {head_drop:.0f}° forward for {inactive:.0f}s "
                    f"— sleep-level head position")
        elif trigger == "recline":
            return (f"Reclined posture ({recline:.0%}) for {inactive:.0f}s")
        else:
            return f"Sleep: inactive {inactive:.0f}s, recline {recline:.0%}"

    elif state == "drowsy":
        parts = []
        if perclos is not None and perclos >= 0.10:
            parts.append(f"PERCLOS={perclos:.0%} eye closure")
        if inactive >= 5:
            parts.append(f"still {inactive:.0f}s")
        if head_drop and head_drop >= 15:
            parts.append(f"head drop {head_drop:.0f}°")
        if recline >= 0.30:
            parts.append(f"reclined {recline:.0%}")
        cause = " + ".join(parts) if parts else f"low activity {inactive:.0f}s"
        return f"Drowsy: {cause}"

    return f"Fatigue state={state}, inactive={inactive:.0f}s"


class FatigueEngine:
    """
    Per-person fatigue episode tracker.
    Records both SLEEPING and DROWSY episodes as FatigueEvents with a
    fatigue_type tag and a fatigue_cause explanation.
    """

    def __init__(self, person_id: int | None = None):
        self._person_id          = person_id
        self._episode_start:     float | None = None
        self._episode_start_dt:  str   | None = None
        self._episode_state:     str   | None = None   # "sleeping" | "drowsy"
        self._last_alert_at:     float | None = None
        self._current_event_id:  int   | None = None

    def update(self, analysis: SleepAnalysis,
               snapshot_frame=None,
               person_bbox: tuple | None = None) -> tuple[bool, float]:
        from app.services.snapshot_service import save_snapshot, save_person_crop
        from app.database.repository import insert_fatigue_event, update_event_end

        now      = time.monotonic()
        now_dt   = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
        state    = analysis.state   # "sleeping" | "drowsy" | "awake" | ...
        is_alert = state in ("sleeping", "drowsy")

        if is_alert:
            # Start episode timer on first alert frame
            if self._episode_start is None:
                self._episode_start    = now
                self._episode_start_dt = now_dt
                self._episode_state    = state
                logger.info(f"[P{self._person_id}] Fatigue episode started: {state}")

            duration    = now - self._episode_start
            in_cooldown = (
                self._last_alert_at is not None
                and (now - self._last_alert_at) < ALERT_COOLDOWN_SECONDS
            )

            if not in_cooldown:
                self._last_alert_at = now

                full_snap = (
                    save_snapshot(snapshot_frame)
                    if snapshot_frame is not None else None
                )
                crop_snap = None
                if snapshot_frame is not None and person_bbox is not None:
                    x1, y1, x2, y2 = person_bbox
                    crop_snap = save_person_crop(
                        snapshot_frame, x1, y1, x2, y2,
                        track_id=self._person_id or 0,
                    )

                cause = _build_cause(state, analysis)

                ev = insert_fatigue_event(
                    person_id        = self._person_id,
                    camera_id        = CAMERA_ID,
                    fatigue_type     = state,             # "sleeping" | "drowsy"
                    fatigue_cause    = cause,
                    started_at       = self._episode_start_dt,
                    ended_at         = None,
                    duration         = round(duration, 1),
                    trigger          = analysis.debug.get("trigger", "unknown"),
                    reclined_ratio   = analysis.reclined_ratio,
                    inactive_seconds = analysis.inactive_seconds,
                    confidence       = analysis.confidence,
                    snapshot         = full_snap,
                    crop_snapshot    = crop_snap,
                    summary          = None,
                )

                if ev:
                    self._current_event_id = ev.id
                    logger.warning(
                        f"[P{self._person_id}] FATIGUE EVENT #{ev.id} "
                        f"type={state} | cause={cause[:60]}"
                    )
                    Thread(
                        target=self._score_async,
                        args=(ev.id, analysis, round(duration, 1), state),
                        daemon=True,
                    ).start()

            return True, round(duration, 1)

        else:
            # Episode ended
            if self._episode_start is not None:
                total   = now - self._episode_start
                now_dt2 = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
                logger.info(
                    f"[P{self._person_id}] Fatigue episode ended "
                    f"({self._episode_state}) after {total:.1f}s"
                )
                if self._current_event_id is not None:
                    eid = self._current_event_id
                    Thread(
                        target=update_event_end,
                        args=(eid, now_dt2, round(total, 1), None),
                        daemon=True,
                    ).start()

            self._episode_start    = None
            self._episode_start_dt = None
            self._episode_state    = None
            self._current_event_id = None

        return False, 0.0

    @staticmethod
    def _score_async(event_id: int, analysis: SleepAnalysis,
                     duration: float, fatigue_type: str):
        """
        Compute risk score and store as summary.
        Runs in background thread — never blocks the main pipeline.
        Replaces the Ollama LLM call entirely.
        """
        from app.database.db import SessionLocal
        from app.database.models import FatigueEvent
        try:
            risk = compute_risk(
                fatigue_type     = fatigue_type,
                inactive_seconds = analysis.inactive_seconds,
                reclined_ratio   = analysis.reclined_ratio,
                confidence       = analysis.confidence,
                duration         = duration,
                signals          = analysis.signals,
                ear_result       = analysis.ear,
            )
            summary_str = risk.to_summary_str()

            db = SessionLocal()
            try:
                ev = db.query(FatigueEvent).filter(FatigueEvent.id == event_id).first()
                if ev:
                    ev.summary   = summary_str
                    ev.confidence= analysis.confidence  # update with latest
                    db.commit()
            finally:
                db.close()

            logger.info(
                f"Risk score P{analysis} event#{event_id}: "
                f"{risk.level} {risk.score}/100 | {risk.onset_pattern}"
            )
        except Exception as e:
            logger.error(f"Risk scoring failed: {e}")