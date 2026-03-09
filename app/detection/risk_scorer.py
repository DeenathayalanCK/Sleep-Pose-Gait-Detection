"""
risk_scorer.py — Deterministic fatigue risk scorer.

Replaces the Ollama LLM summariser entirely.

WHY:
  The LLM generated vague, non-actionable sentences like
  "This may indicate fatigue." It added a 2–3 second delay,
  required a running Ollama container, and produced output
  that couldn't be aggregated or compared across events.

WHAT THIS DOES:
  Computes a 0–100 risk score from the actual signal values
  at event time, with weighted contributions from each signal.
  Produces a structured dict that is:
    - Stored in the DB (replaces the 'summary' text field)
    - Shown in the UI as a risk badge + factor breakdown
    - Aggregatable across shifts/persons for analytics

SIGNAL WEIGHTS (sum to 1.0):
  PERCLOS (eye closure rate)   0.30  — most direct physiological signal
  Head drop trajectory         0.25  — gradual vs sudden onset
  Inactivity duration          0.20  — time without movement
  Recline ratio                0.15  — body angle
  Wrist activity absence       0.10  — hands idle = not working

ONSET PATTERN:
  "gradual" — signals built up over >60s (fatigue accumulation)
  "sudden"  — signals appeared within <15s (possible medical event)
  This distinction matters: sudden onset warrants immediate attention.
"""
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RiskScore:
    score:          int           = 0       # 0–100
    level:          str           = "LOW"   # LOW / MEDIUM / HIGH / CRITICAL
    factors:        list          = field(default_factory=list)   # human-readable reasons
    onset_pattern:  str           = "unknown"   # "gradual" | "sudden" | "sustained"
    signal_scores:  dict          = field(default_factory=dict)   # per-signal contribution
    recommendation: str           = ""

    def to_dict(self) -> dict:
        return {
            "score":         self.score,
            "level":         self.level,
            "factors":       self.factors,
            "onset_pattern": self.onset_pattern,
            "signal_scores": self.signal_scores,
            "recommendation":self.recommendation,
        }

    def to_summary_str(self) -> str:
        """Compact string stored in DB summary field — human readable."""
        factors_str = "; ".join(self.factors[:3])
        return (f"[{self.level}] Risk={self.score}/100 | "
                f"Onset={self.onset_pattern} | {factors_str}")


def compute_risk(
    fatigue_type:     str,
    inactive_seconds: float,
    reclined_ratio:   float,
    confidence:       float,
    duration:         float,
    signals:          Optional[dict] = None,
    ear_result=None,         # EARResult or None
    z_result=None,           # ZScoreResult or None
) -> RiskScore:
    """
    Compute risk score from all available signals at event time.

    Parameters mirror what FatigueEngine has when an event fires.
    All inputs are optional — score degrades gracefully when signals
    are unavailable (e.g. no face visible for EAR).
    """
    signals     = signals or {}
    factors     = []
    sig_scores  = {}
    total       = 0.0

    # ── Signal 1: PERCLOS / EAR (weight 0.30) ────────────────────────
    perclos = ear_result.perclos if ear_result and ear_result.face_found else None
    if perclos is not None:
        ear_contribution = min(1.0, perclos / 0.40) * 0.30
        sig_scores["perclos"] = round(ear_contribution * 100, 1)
        total += ear_contribution
        if perclos >= 0.40:
            factors.append(f"Eyes closed {perclos:.0%} of last 60 frames (PERCLOS={perclos:.2f})")
        elif perclos >= 0.15:
            factors.append(f"Partial eye closure detected (PERCLOS={perclos:.2f})")
    else:
        # Face not visible — redistribute weight to next best signal
        # Inactivity absorbs the EAR weight when EAR is unavailable
        pass

    # ── Signal 2: Head drop angle (weight 0.25) ───────────────────────
    head_drop = signals.get("head_drop_angle")
    if head_drop is not None:
        # 0° = upright, 40°+ = clearly drooping
        head_contribution = min(1.0, max(0.0, (head_drop - 10.0) / 30.0)) * 0.25
        sig_scores["head_drop"] = round(head_contribution * 100, 1)
        total += head_contribution
        if head_drop >= 35:
            factors.append(f"Head drooped {head_drop:.0f}° forward (sleep-level drop)")
        elif head_drop >= 20:
            factors.append(f"Head tilted {head_drop:.0f}° forward (drowsy indicator)")

    # ── Signal 3: Inactivity duration (weight 0.20 + EAR fallback) ───
    inact_weight = 0.20 if perclos is not None else 0.50  # absorb EAR weight
    inact_norm   = min(1.0, inactive_seconds / 60.0)       # 60s = full score
    inact_contribution = inact_norm * inact_weight
    sig_scores["inactivity"] = round(inact_contribution * 100, 1)
    total += inact_contribution
    if inactive_seconds >= 30:
        factors.append(f"No movement for {inactive_seconds:.0f}s")
    elif inactive_seconds >= 10:
        factors.append(f"Low activity — still for {inactive_seconds:.0f}s")

    # ── Signal 4: Recline ratio (weight 0.15) ─────────────────────────
    recline_contribution = min(1.0, max(0.0, (reclined_ratio - 0.30) / 0.30)) * 0.15
    sig_scores["recline"] = round(recline_contribution * 100, 1)
    total += recline_contribution
    if reclined_ratio >= 0.50:
        factors.append(f"Body reclined at {reclined_ratio:.0%} (lying posture)")
    elif reclined_ratio >= 0.38:
        factors.append(f"Forward-leaning posture ({reclined_ratio:.0%} recline)")

    # ── Signal 5: Wrist activity absence (weight 0.10) ────────────────
    wrist_act = signals.get("wrist_activity")
    if wrist_act is not None:
        # Low wrist movement = idle hands = not working
        wrist_idle       = 1.0 - min(1.0, wrist_act / 0.01)
        wrist_contribution = wrist_idle * 0.10
        sig_scores["wrist_idle"] = round(wrist_contribution * 100, 1)
        total += wrist_contribution
        if wrist_idle > 0.8:
            factors.append("Hands completely still (no keyboard/mouse activity)")

    # ── Spine angle bonus ─────────────────────────────────────────────
    spine = signals.get("spine_angle")
    if spine is not None and spine >= 35:
        bonus = min(0.05, (spine - 35) / 100)
        total += bonus
        if spine >= 45:
            factors.append(f"Spine tilted {spine:.0f}° from vertical")

    # ── Z-score baseline deviation (weight 0.20 additive) ─────────────
    # When a person's own baseline is available, their personal deviation
    # carries significant evidential weight — it adapts to individual norms.
    if z_result is not None and z_result.baseline_ready:
        max_z = z_result.max_z
        if max_z >= 2.0:
            # Scale: 2σ = 0.08 contribution, 4σ = 0.20 (capped)
            z_contribution = min(0.20, (max_z - 2.0) / 10.0 + 0.08)
            sig_scores["z_score"] = round(z_contribution * 100, 1)
            total += z_contribution
            z_sig = z_result.triggered_signal or "posture"
            if max_z >= 3.0:
                factors.append(
                    f"{z_sig} is {max_z:.1f}σ above this person's normal "
                    f"(personal baseline — {z_result.samples_collected} samples)"
                )
            else:
                factors.append(
                    f"{z_sig} {max_z:.1f}σ above personal baseline"
                )

    # ── Final score ───────────────────────────────────────────────────
    # Clip and scale to 0–100, bias upward for confirmed fatigue type
    base_score = min(1.0, total)
    if fatigue_type == "sleeping":
        base_score = max(base_score, 0.50)   # sleeping is always at least 50
    elif fatigue_type == "drowsy":
        base_score = max(base_score, 0.30)

    # Confidence from pose detector modulates score slightly
    score = int(base_score * 100 * (0.7 + 0.3 * confidence))
    score = max(0, min(100, score))

    # ── Risk level ────────────────────────────────────────────────────
    if score >= 75:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    # ── Onset pattern ─────────────────────────────────────────────────
    if duration < 15:
        onset = "sudden"    # appeared very quickly — possible medical concern
    elif duration < 60:
        onset = "gradual"   # built up over a minute
    else:
        onset = "sustained" # ongoing for a long time

    # ── Recommendation ────────────────────────────────────────────────
    if level == "CRITICAL":
        rec = "Immediate check required — person may be asleep on duty."
    elif level == "HIGH":
        rec = "Alert supervisor — sustained fatigue indicators across multiple signals."
    elif level == "MEDIUM":
        rec = "Monitor closely — early fatigue signs detected."
    else:
        rec = "Low risk — continue monitoring."

    if onset == "sudden" and score >= 50:
        rec = "⚠ Sudden onset — verify person is well. " + rec

    if not factors:
        factors = [f"Fatigue state '{fatigue_type}' detected with {confidence:.0%} confidence"]

    return RiskScore(
        score         = score,
        level         = level,
        factors       = factors,
        onset_pattern = onset,
        signal_scores = sig_scores,
        recommendation= rec,
    )