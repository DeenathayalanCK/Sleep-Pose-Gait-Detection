"""
evaluation_routes.py — REST endpoints for ground truth labelling + metrics.

GET  /evaluate/events          — unlabelled events (need human review)
GET  /evaluate/labels          — all existing labels
POST /evaluate/label           — submit a label (TP/FP/FN)
DELETE /evaluate/label/{id}    — remove a label (reviewer corrected mistake)
GET  /evaluate/metrics         — computed precision/recall/F1/latency
GET  /evaluate/metrics/export  — export labels as CSV for external analysis
"""
import csv
import io
import logging
import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.database.repository import (
    insert_ground_truth, get_all_labels,
    delete_label, get_unlabelled_events, get_all_events,
)
from app.evaluation.metrics import compute_metrics

logger      = logging.getLogger(__name__)
eval_router = APIRouter()


class LabelInput(BaseModel):
    event_id:      Optional[int]   = None
    person_id:     Optional[int]   = None
    camera_id:     str             = "unknown"
    label_type:    str
    fatigue_type:  str
    started_at:    str
    ended_at:      Optional[str]   = None
    duration:      Optional[float] = None
    notes:         Optional[str]   = None
    labelled_by:   Optional[str]   = None
    detection_lag: Optional[float] = None


@eval_router.get("/evaluate/events")
def get_unlabelled():
    events = get_unlabelled_events()
    return {"count": len(events), "events": [e.to_dict() for e in events]}


@eval_router.get("/evaluate/labels")
def get_labels():
    labels = get_all_labels()
    return {"count": len(labels), "labels": [l.to_dict() for l in labels]}


@eval_router.post("/evaluate/label")
def submit_label(inp: LabelInput):
    if inp.label_type not in ("TP", "FP", "FN"):
        return {"error": "label_type must be TP, FP, or FN"}
    if inp.fatigue_type not in ("sleeping", "drowsy"):
        return {"error": "fatigue_type must be sleeping or drowsy"}
    row = insert_ground_truth(
        event_id=inp.event_id, person_id=inp.person_id,
        camera_id=inp.camera_id, label_type=inp.label_type,
        fatigue_type=inp.fatigue_type, started_at=inp.started_at,
        ended_at=inp.ended_at, duration=inp.duration,
        notes=inp.notes, labelled_by=inp.labelled_by,
        detection_lag=inp.detection_lag,
    )
    if row:
        return {"ok": True, "label_id": row.id}
    return {"error": "DB insert failed"}


@eval_router.delete("/evaluate/label/{label_id}")
def remove_label(label_id: int):
    return {"ok": delete_label(label_id)}


@eval_router.get("/evaluate/metrics")
def get_metrics(
    camera_id:       Optional[str]   = None,
    fatigue_type:    Optional[str]   = None,
    monitored_hours: Optional[float] = None,
):
    result = compute_metrics(
        camera_id=camera_id,
        fatigue_type=fatigue_type,
        monitored_hours=monitored_hours,
    )
    return result.to_dict()


@eval_router.get("/evaluate/metrics/export")
def export_labels_csv(camera_id: Optional[str] = None):
    labels = get_all_labels(camera_id)
    events = {e.id: e for e in get_all_events()}
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "label_id","label_type","fatigue_type","event_id","person_id",
        "camera_id","started_at","ended_at","duration","detection_lag",
        "system_trigger","system_confidence","notes","labelled_by","labelled_at",
    ])
    writer.writeheader()
    for lbl in labels:
        ev = events.get(lbl.event_id) if lbl.event_id else None
        writer.writerow({
            "label_id": lbl.id, "label_type": lbl.label_type,
            "fatigue_type": lbl.fatigue_type, "event_id": lbl.event_id,
            "person_id": lbl.person_id, "camera_id": lbl.camera_id,
            "started_at": lbl.started_at, "ended_at": lbl.ended_at,
            "duration": lbl.duration, "detection_lag": lbl.detection_lag,
            "system_trigger": ev.trigger if ev else "",
            "system_confidence": ev.confidence if ev else "",
            "notes": lbl.notes or "", "labelled_by": lbl.labelled_by or "",
            "labelled_at": lbl.labelled_at or "",
        })
    output.seek(0)
    fname = f"eval_labels_{datetime.date.today()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )