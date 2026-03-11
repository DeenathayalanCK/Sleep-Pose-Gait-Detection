"""
metrics.py — Evaluation metric computation from ground truth labels.

ALL metrics computed from the GroundTruthLabel table populated by
the human reviewer through the Evaluate tab in the frontend.

Metrics computed:
  Precision        = TP / (TP + FP)      — of alerts fired, how many were real
  Recall           = TP / (TP + FN)      — of real events, how many were caught
  F1               = 2 * P * R / (P + R) — harmonic mean
  False positive rate per hour           — FP / total_monitored_hours
  Mean detection latency (seconds)       — avg lag from onset to alert (TP only)
  Confusion breakdown by trigger         — which triggers cause most FP
  Per-fatigue-type breakdown             — sleeping vs drowsy separately
"""
import logging
from dataclasses import dataclass, field
from typing import Optional
from app.database.repository import get_all_labels, get_all_events

logger = logging.getLogger(__name__)


@dataclass
class MetricResult:
    # Core detection metrics
    precision:          Optional[float] = None
    recall:             Optional[float] = None
    f1:                 Optional[float] = None

    # Counts
    tp:   int = 0
    fp:   int = 0
    fn:   int = 0
    total_labelled: int = 0

    # False positive rate
    fp_per_hour:         Optional[float] = None
    monitored_hours:     float = 0.0

    # Detection latency (seconds from real onset to system alert)
    mean_detection_lag:  Optional[float] = None
    min_detection_lag:   Optional[float] = None
    max_detection_lag:   Optional[float] = None

    # Breakdowns
    by_fatigue_type:  dict = field(default_factory=dict)  # sleeping/drowsy separately
    by_trigger:       dict = field(default_factory=dict)  # which triggers caused FP
    unlabelled_count: int  = 0

    # Status
    enough_data:      bool = False
    message:          str  = ""

    def to_dict(self) -> dict:
        return {
            "precision":         round(self.precision, 3) if self.precision is not None else None,
            "recall":            round(self.recall,    3) if self.recall    is not None else None,
            "f1":                round(self.f1,        3) if self.f1        is not None else None,
            "tp":                self.tp,
            "fp":                self.fp,
            "fn":                self.fn,
            "total_labelled":    self.total_labelled,
            "fp_per_hour":       round(self.fp_per_hour, 3) if self.fp_per_hour is not None else None,
            "monitored_hours":   round(self.monitored_hours, 2),
            "mean_detection_lag":round(self.mean_detection_lag, 1) if self.mean_detection_lag is not None else None,
            "min_detection_lag": round(self.min_detection_lag,  1) if self.min_detection_lag  is not None else None,
            "max_detection_lag": round(self.max_detection_lag,  1) if self.max_detection_lag  is not None else None,
            "by_fatigue_type":   self.by_fatigue_type,
            "by_trigger":        self.by_trigger,
            "unlabelled_count":  self.unlabelled_count,
            "enough_data":       self.enough_data,
            "message":           self.message,
        }


def compute_metrics(camera_id: str = None,
                    fatigue_type: str = None,
                    monitored_hours: float = None) -> MetricResult:
    """
    Compute all evaluation metrics from ground truth labels in DB.

    Args:
        camera_id:       filter to specific camera (None = all cameras)
        fatigue_type:    filter to "sleeping" or "drowsy" (None = both)
        monitored_hours: total hours the system was running (for FP/hr rate).
                         If None, estimated from event timestamps.
    """
    labels = get_all_labels(camera_id)
    events = get_all_events()

    if not labels:
        return MetricResult(
            enough_data = False,
            message     = "No ground truth labels yet. Use the Evaluate tab to label events.",
            unlabelled_count = len(events),
        )

    # Filter by fatigue type if specified
    if fatigue_type:
        labels = [l for l in labels if l.fatigue_type == fatigue_type]

    # Count unlabelled events
    labelled_event_ids = {l.event_id for l in labels if l.event_id is not None}
    unlabelled = [e for e in events if e.id not in labelled_event_ids]

    tp_labels = [l for l in labels if l.label_type == "TP"]
    fp_labels = [l for l in labels if l.label_type == "FP"]
    fn_labels = [l for l in labels if l.label_type == "FN"]

    tp = len(tp_labels)
    fp = len(fp_labels)
    fn = len(fn_labels)

    if tp + fp + fn < 5:
        return MetricResult(
            tp=tp, fp=fp, fn=fn,
            total_labelled = tp + fp + fn,
            unlabelled_count = len(unlabelled),
            enough_data = False,
            message = f"Only {tp+fp+fn} labels — need at least 5 to compute reliable metrics. Keep labelling.",
        )

    # ── Core metrics ──────────────────────────────────────────────────────────
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall    = tp / (tp + fn) if (tp + fn) > 0 else None
    f1        = (2 * precision * recall / (precision + recall)
                 if precision and recall else None)

    # ── Detection latency (TP only) ───────────────────────────────────────────
    lags = [l.detection_lag for l in tp_labels if l.detection_lag is not None]
    mean_lag = sum(lags) / len(lags) if lags else None
    min_lag  = min(lags) if lags else None
    max_lag  = max(lags) if lags else None

    # ── FP per hour ───────────────────────────────────────────────────────────
    if monitored_hours is None:
        # Estimate from event timestamps if not provided
        monitored_hours = _estimate_monitored_hours(events)

    fp_per_hour = fp / monitored_hours if monitored_hours > 0 else None

    # ── Breakdown by fatigue type ─────────────────────────────────────────────
    by_type = {}
    for ftype in ["sleeping", "drowsy"]:
        t_labels = [l for l in labels if l.fatigue_type == ftype]
        t_tp = sum(1 for l in t_labels if l.label_type == "TP")
        t_fp = sum(1 for l in t_labels if l.label_type == "FP")
        t_fn = sum(1 for l in t_labels if l.label_type == "FN")
        t_prec = t_tp / (t_tp + t_fp) if (t_tp + t_fp) > 0 else None
        t_rec  = t_tp / (t_tp + t_fn) if (t_tp + t_fn) > 0 else None
        by_type[ftype] = {
            "tp": t_tp, "fp": t_fp, "fn": t_fn,
            "precision": round(t_prec, 3) if t_prec is not None else None,
            "recall":    round(t_rec,  3) if t_rec  is not None else None,
        }

    # ── FP breakdown by trigger ───────────────────────────────────────────────
    # Which triggers are causing the most false positives
    fp_event_ids = {l.event_id for l in fp_labels if l.event_id is not None}
    by_trigger   = {}
    for ev in events:
        if ev.id in fp_event_ids and ev.trigger:
            by_trigger[ev.trigger] = by_trigger.get(ev.trigger, 0) + 1

    # ── Build summary message ─────────────────────────────────────────────────
    msg_parts = []
    if precision is not None:
        msg_parts.append(f"Precision={precision:.0%}")
    if recall is not None:
        msg_parts.append(f"Recall={recall:.0%}")
    if fp_per_hour is not None:
        msg_parts.append(f"FP/hr={fp_per_hour:.2f}")
    if mean_lag is not None:
        msg_parts.append(f"Avg latency={mean_lag:.1f}s")

    return MetricResult(
        precision         = precision,
        recall            = recall,
        f1                = f1,
        tp                = tp,
        fp                = fp,
        fn                = fn,
        total_labelled    = tp + fp + fn,
        fp_per_hour       = fp_per_hour,
        monitored_hours   = monitored_hours,
        mean_detection_lag= mean_lag,
        min_detection_lag = min_lag,
        max_detection_lag = max_lag,
        by_fatigue_type   = by_type,
        by_trigger        = by_trigger,
        unlabelled_count  = len(unlabelled),
        enough_data       = True,
        message           = " | ".join(msg_parts),
    )


def _estimate_monitored_hours(events) -> float:
    """
    Estimate total monitored hours from the event timestamps.
    Uses the span from earliest to latest event as a proxy.
    Not accurate — provide actual hours via the UI for precise FP/hr.
    """
    if not events:
        return 0.0
    try:
        from datetime import datetime
        times = []
        for e in events:
            try:
                times.append(datetime.fromisoformat(e.started_at))
            except Exception:
                pass
        if len(times) < 2:
            return 1.0
        span = (max(times) - min(times)).total_seconds() / 3600.0
        return max(span, 0.1)
    except Exception:
        return 1.0