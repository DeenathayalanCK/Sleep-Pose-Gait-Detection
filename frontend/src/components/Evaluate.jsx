import { useEffect, useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

function imgUrl(path) {
  if (!path) return null;
  return `${API}/snapshots/${path.split(/[\\/]/).pop()}`;
}
function fmt(iso) {
  return iso ? iso.slice(0, 19).replace("T", " ") : "—";
}

const LABEL_CFG = {
  TP: {
    color: "#00e676",
    bg: "#00e67618",
    label: "✓ TRUE POSITIVE",
    desc: "Real event — correctly detected",
  },
  FP: {
    color: "#ff2020",
    bg: "#ff202018",
    label: "✗ FALSE POSITIVE",
    desc: "Not real — system was wrong",
  },
  FN: {
    color: "#ff8c00",
    bg: "#ff8c0018",
    label: "⚠ MISSED (FN)",
    desc: "Real event the system missed",
  },
};

function MetricCard({ label, value, sub, color = "#00bcd4" }) {
  return (
    <div
      style={{
        background: "#0a0a0a",
        border: `1px solid ${color}22`,
        borderTop: `2px solid ${color}`,
        borderRadius: 8,
        padding: "14px 16px",
        minWidth: 110,
      }}
    >
      <div
        style={{
          fontSize: 9,
          color: "#444",
          letterSpacing: 2,
          textTransform: "uppercase",
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 22,
          fontFamily: "monospace",
          fontWeight: 700,
          color,
        }}
      >
        {value ?? "—"}
      </div>
      {sub && (
        <div style={{ fontSize: 9, color: "#333", marginTop: 3 }}>{sub}</div>
      )}
    </div>
  );
}

function ProgressBar({ value, color }) {
  return (
    <div
      style={{
        background: "#111",
        borderRadius: 4,
        height: 6,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width: `${Math.min(100, (value || 0) * 100)}%`,
          height: "100%",
          background: color,
          borderRadius: 4,
          transition: "width 0.4s",
        }}
      />
    </div>
  );
}

function LabelButton({ type, active, onClick }) {
  const cfg = LABEL_CFG[type];
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? cfg.bg : "transparent",
        border: `1px solid ${active ? cfg.color : "#1a1a1a"}`,
        borderRadius: 6,
        padding: "6px 14px",
        cursor: "pointer",
        color: active ? cfg.color : "#333",
        fontSize: 10,
        fontFamily: "monospace",
        letterSpacing: 1,
        fontWeight: active ? 700 : 400,
        transition: "all 0.15s",
      }}
    >
      {cfg.label}
    </button>
  );
}

function EventLabeller({ event, onLabelled }) {
  const [label, setLabel] = useState(null);
  const [lag, setLag] = useState("");
  const [notes, setNotes] = useState("");
  const [reviewer, setReviewer] = useState(
    localStorage.getItem("reviewer_name") || "",
  );
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const cropUrl = imgUrl(event.crop_snapshot);
  const fullUrl = imgUrl(event.snapshot);
  const cfg = label ? LABEL_CFG[label] : null;

  const save = async () => {
    if (!label) return;
    setSaving(true);
    localStorage.setItem("reviewer_name", reviewer);
    try {
      await axios.post(`${API}/evaluate/label`, {
        event_id: event.id,
        person_id: event.person_id,
        camera_id: event.camera_id,
        label_type: label,
        fatigue_type: event.fatigue_type,
        started_at: event.started_at,
        ended_at: event.ended_at,
        duration: event.duration,
        notes: notes || null,
        labelled_by: reviewer || null,
        detection_lag: label === "TP" && lag ? parseFloat(lag) : null,
      });
      setSaved(true);
      setTimeout(() => onLabelled(event.id), 600);
    } catch (e) {
      alert("Save failed: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        background: "#0d0d0d",
        border: `1px solid ${cfg ? cfg.color + "44" : "#1a1a1a"}`,
        borderLeft: `3px solid ${cfg ? cfg.color : "#222"}`,
        borderRadius: 8,
        padding: 16,
        marginBottom: 10,
      }}
    >
      <div
        style={{ display: "grid", gridTemplateColumns: "100px 1fr", gap: 14 }}
      >
        {/* Image */}
        <div>
          {cropUrl ? (
            <img
              src={cropUrl}
              style={{
                width: 100,
                height: 130,
                objectFit: "cover",
                borderRadius: 6,
                border: "1px solid #2a2a2a",
              }}
              alt=""
            />
          ) : (
            <div
              style={{
                width: 100,
                height: 130,
                background: "#111",
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 9,
                color: "#333",
              }}
            >
              NO CROP
            </div>
          )}
          {fullUrl && (
            <img
              src={fullUrl}
              style={{
                width: 100,
                height: 56,
                objectFit: "cover",
                borderRadius: 4,
                marginTop: 4,
                border: "1px solid #1a1a1a",
                opacity: 0.5,
              }}
              alt=""
            />
          )}
        </div>

        {/* Right side */}
        <div>
          {/* Header */}
          <div
            style={{
              display: "flex",
              gap: 10,
              alignItems: "center",
              marginBottom: 8,
              flexWrap: "wrap",
            }}
          >
            <span
              style={{
                fontFamily: "monospace",
                fontSize: 12,
                color:
                  event.fatigue_type === "sleeping" ? "#ff2020" : "#ff8c00",
                fontWeight: 700,
              }}
            >
              {event.fatigue_type === "sleeping" ? "😴" : "😪"}{" "}
              {event.fatigue_type.toUpperCase()}
            </span>
            <span
              style={{ fontSize: 10, color: "#444", fontFamily: "monospace" }}
            >
              P{event.person_id} · #{event.id} · {fmt(event.started_at)}
            </span>
            <span
              style={{ fontSize: 9, color: "#333", fontFamily: "monospace" }}
            >
              dur={event.duration?.toFixed(1)}s · inactive=
              {event.inactive_seconds?.toFixed(0)}s · trigger={event.trigger}
            </span>
          </div>

          {/* Cause */}
          {event.fatigue_cause && (
            <div
              style={{
                fontSize: 10,
                color: "#555",
                marginBottom: 10,
                fontFamily: "monospace",
                lineHeight: 1.5,
              }}
            >
              {event.fatigue_cause}
            </div>
          )}

          {/* Label buttons */}
          <div
            style={{
              display: "flex",
              gap: 6,
              marginBottom: 10,
              flexWrap: "wrap",
            }}
          >
            {["TP", "FP"].map((t) => (
              <LabelButton
                key={t}
                type={t}
                active={label === t}
                onClick={() => setLabel(label === t ? null : t)}
              />
            ))}
          </div>

          {/* Detection lag — only for TP */}
          {label === "TP" && (
            <div style={{ marginBottom: 8 }}>
              <div
                style={{
                  fontSize: 9,
                  color: "#444",
                  marginBottom: 3,
                  letterSpacing: 1,
                }}
              >
                DETECTION LAG (seconds from actual sleep onset to first alert)
              </div>
              <input
                type="number"
                placeholder="e.g. 18"
                value={lag}
                onChange={(e) => setLag(e.target.value)}
                style={{
                  background: "#111",
                  border: "1px solid #2a2a2a",
                  borderRadius: 4,
                  padding: "4px 8px",
                  color: "#ccc",
                  fontSize: 11,
                  fontFamily: "monospace",
                  width: 100,
                }}
              />
              <span style={{ fontSize: 9, color: "#333", marginLeft: 8 }}>
                Optional — leave blank if unknown
              </span>
            </div>
          )}

          {/* Notes + reviewer */}
          <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
            <input
              placeholder="Notes (optional)..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              style={{
                flex: 1,
                background: "#111",
                border: "1px solid #1a1a1a",
                borderRadius: 4,
                padding: "4px 8px",
                color: "#888",
                fontSize: 10,
                fontFamily: "monospace",
              }}
            />
            <input
              placeholder="Your name"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              style={{
                width: 100,
                background: "#111",
                border: "1px solid #1a1a1a",
                borderRadius: 4,
                padding: "4px 8px",
                color: "#888",
                fontSize: 10,
                fontFamily: "monospace",
              }}
            />
          </div>

          {/* Save */}
          <button
            onClick={save}
            disabled={!label || saving || saved}
            style={{
              background: saved ? "#00e67618" : label ? "#ffffff0f" : "#0a0a0a",
              border: `1px solid ${saved ? "#00e676" : label ? "#444" : "#1a1a1a"}`,
              borderRadius: 6,
              padding: "6px 20px",
              cursor: label ? "pointer" : "default",
              color: saved ? "#00e676" : label ? "#ccc" : "#2a2a2a",
              fontSize: 10,
              fontFamily: "monospace",
              letterSpacing: 1,
            }}
          >
            {saved ? "✓ Saved" : saving ? "Saving…" : "Save Label"}
          </button>
        </div>
      </div>
    </div>
  );
}

function AddFNForm({ onAdded }) {
  const [open, setOpen] = useState(false);
  const [ftype, setFtype] = useState("sleeping");
  const [personId, setPersonId] = useState("");
  const [start, setStart] = useState("");
  const [dur, setDur] = useState("");
  const [notes, setNotes] = useState("");
  const [reviewer, setReviewer] = useState(
    localStorage.getItem("reviewer_name") || "",
  );
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!start) return;
    setSaving(true);
    try {
      await axios.post(`${API}/evaluate/label`, {
        event_id: null,
        person_id: personId ? parseInt(personId) : null,
        camera_id: "second_floor_middle",
        label_type: "FN",
        fatigue_type: ftype,
        started_at: start,
        duration: dur ? parseFloat(dur) : null,
        notes,
        labelled_by: reviewer || null,
      });
      setOpen(false);
      setStart("");
      setDur("");
      setNotes("");
      setPersonId("");
      onAdded();
    } catch (e) {
      alert("Failed: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  if (!open)
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          background: "transparent",
          border: "1px dashed #2a2a2a",
          borderRadius: 6,
          padding: "7px 16px",
          cursor: "pointer",
          color: "#ff8c00",
          fontSize: 10,
          fontFamily: "monospace",
        }}
      >
        + Add Missed Event (False Negative)
      </button>
    );

  return (
    <div
      style={{
        background: "#0d0d0d",
        border: "1px solid #ff8c0044",
        borderLeft: "3px solid #ff8c00",
        borderRadius: 8,
        padding: 14,
        marginBottom: 10,
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: "#ff8c00",
          marginBottom: 10,
          fontFamily: "monospace",
          fontWeight: 700,
        }}
      >
        ⚠ ADD MISSED EVENT — system never fired but person was really
        asleep/drowsy
      </div>
      <div
        style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}
      >
        {["sleeping", "drowsy"].map((t) => (
          <button
            key={t}
            onClick={() => setFtype(t)}
            style={{
              background: ftype === t ? "#ff8c0018" : "transparent",
              border: `1px solid ${ftype === t ? "#ff8c00" : "#1a1a1a"}`,
              borderRadius: 5,
              padding: "4px 12px",
              cursor: "pointer",
              color: ftype === t ? "#ff8c00" : "#444",
              fontSize: 10,
              fontFamily: "monospace",
            }}
          >
            {t}
          </button>
        ))}
        <input
          placeholder="Person ID"
          value={personId}
          onChange={(e) => setPersonId(e.target.value)}
          style={{
            width: 80,
            background: "#111",
            border: "1px solid #1a1a1a",
            borderRadius: 4,
            padding: "4px 8px",
            color: "#888",
            fontSize: 10,
            fontFamily: "monospace",
          }}
        />
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 9, color: "#444", marginBottom: 2 }}>
            STARTED AT (e.g. 2026-03-09 06:42:00)
          </div>
          <input
            placeholder="2026-03-09 06:42:00"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            style={{
              width: 180,
              background: "#111",
              border: "1px solid #1a1a1a",
              borderRadius: 4,
              padding: "4px 8px",
              color: "#ccc",
              fontSize: 10,
              fontFamily: "monospace",
            }}
          />
        </div>
        <div>
          <div style={{ fontSize: 9, color: "#444", marginBottom: 2 }}>
            DURATION (s)
          </div>
          <input
            placeholder="e.g. 45"
            value={dur}
            onChange={(e) => setDur(e.target.value)}
            type="number"
            style={{
              width: 80,
              background: "#111",
              border: "1px solid #1a1a1a",
              borderRadius: 4,
              padding: "4px 8px",
              color: "#ccc",
              fontSize: 10,
              fontFamily: "monospace",
            }}
          />
        </div>
        <div>
          <div style={{ fontSize: 9, color: "#444", marginBottom: 2 }}>
            YOUR NAME
          </div>
          <input
            placeholder="reviewer"
            value={reviewer}
            onChange={(e) => setReviewer(e.target.value)}
            style={{
              width: 100,
              background: "#111",
              border: "1px solid #1a1a1a",
              borderRadius: 4,
              padding: "4px 8px",
              color: "#ccc",
              fontSize: 10,
              fontFamily: "monospace",
            }}
          />
        </div>
      </div>
      <input
        placeholder="Notes..."
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        style={{
          width: "100%",
          background: "#111",
          border: "1px solid #1a1a1a",
          borderRadius: 4,
          padding: "4px 8px",
          color: "#888",
          fontSize: 10,
          fontFamily: "monospace",
          marginBottom: 8,
          boxSizing: "border-box",
        }}
      />
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={save}
          disabled={!start || saving}
          style={{
            background: "#ff8c0018",
            border: "1px solid #ff8c00",
            borderRadius: 5,
            padding: "5px 14px",
            cursor: "pointer",
            color: "#ff8c00",
            fontSize: 10,
            fontFamily: "monospace",
          }}
        >
          {saving ? "Saving…" : "Save FN"}
        </button>
        <button
          onClick={() => setOpen(false)}
          style={{
            background: "transparent",
            border: "1px solid #1a1a1a",
            borderRadius: 5,
            padding: "5px 14px",
            cursor: "pointer",
            color: "#333",
            fontSize: 10,
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function Evaluate() {
  const [tab, setTab] = useState("label");
  const [unlabelled, setUnlabelled] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [labels, setLabels] = useState([]);
  const [monHours, setMonHours] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [loading, setLoading] = useState(false);

  const loadUnlabelled = () =>
    axios
      .get(`${API}/evaluate/events`)
      .then((r) => setUnlabelled(r.data.events || []))
      .catch(() => {});

  const loadLabels = () =>
    axios
      .get(`${API}/evaluate/labels`)
      .then((r) => setLabels(r.data.labels || []))
      .catch(() => {});

  const loadMetrics = () => {
    setLoading(true);
    const params = {};
    if (monHours) params.monitored_hours = parseFloat(monHours);
    if (filterType !== "all") params.fatigue_type = filterType;
    axios
      .get(`${API}/evaluate/metrics`, { params })
      .then((r) => setMetrics(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadUnlabelled();
    loadLabels();
  }, []);
  useEffect(() => {
    if (tab === "metrics") loadMetrics();
  }, [tab]);

  const handleLabelled = (id) => {
    setUnlabelled((prev) => prev.filter((e) => e.id !== id));
    loadLabels();
  };

  const deleteLabel = async (id) => {
    await axios.delete(`${API}/evaluate/label/${id}`);
    loadLabels();
    loadUnlabelled();
  };

  const tp = labels.filter((l) => l.label_type === "TP").length;
  const fp = labels.filter((l) => l.label_type === "FP").length;
  const fn = labels.filter((l) => l.label_type === "FN").length;

  return (
    <div style={{ fontFamily: "monospace", color: "#ccc" }}>
      {/* Tab nav */}
      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 20,
          borderBottom: "1px solid #111",
          paddingBottom: 10,
        }}
      >
        {[
          {
            key: "label",
            label: `🏷 LABEL EVENTS  (${unlabelled.length} pending)`,
          },
          { key: "metrics", label: "📊 METRICS" },
          { key: "history", label: `📋 HISTORY  (${labels.length})` },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              background: tab === t.key ? "#111" : "transparent",
              border: `1px solid ${tab === t.key ? "#444" : "#1a1a1a"}`,
              borderRadius: 6,
              padding: "5px 14px",
              cursor: "pointer",
              color: tab === t.key ? "#ddd" : "#444",
              fontSize: 10,
              letterSpacing: 1,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── LABEL tab ─────────────────────────────────────────────────────── */}
      {tab === "label" && (
        <div>
          <div
            style={{
              background: "#080808",
              border: "1px solid #0d0d0d",
              borderLeft: "3px solid #00bcd4",
              borderRadius: 8,
              padding: "10px 14px",
              marginBottom: 16,
              fontSize: 10,
              color: "#444",
              lineHeight: 1.9,
            }}
          >
            <span style={{ color: "#00bcd4", fontWeight: 700 }}>
              HOW TO LABEL
            </span>
            <br />
            For each event below: look at the crop photo + cause description.
            <br />
            Mark <span style={{ color: "#00e676" }}>✓ TRUE POSITIVE</span> if
            the person was really sleeping/drowsy.
            <br />
            Mark <span style={{ color: "#ff2020" }}>✗ FALSE POSITIVE</span> if
            the system was wrong (false alarm).
            <br />
            For events the system <b>missed entirely</b>, click Add Missed Event
            below.
            <br />
            For TP events, enter how many seconds after actual onset the alert
            fired.
          </div>

          <div
            style={{
              display: "flex",
              gap: 8,
              marginBottom: 16,
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ display: "flex", gap: 12, fontSize: 10 }}>
              <span style={{ color: "#00e676" }}>TP: {tp}</span>
              <span style={{ color: "#ff2020" }}>FP: {fp}</span>
              <span style={{ color: "#ff8c00" }}>FN: {fn}</span>
              <span style={{ color: "#444" }}>
                Pending: {unlabelled.length}
              </span>
            </div>
            <a
              href={`${API}/evaluate/metrics/export`}
              style={{
                fontSize: 9,
                color: "#333",
                textDecoration: "none",
                border: "1px solid #1a1a1a",
                borderRadius: 4,
                padding: "3px 10px",
              }}
            >
              ↓ Export CSV
            </a>
          </div>

          <AddFNForm
            onAdded={() => {
              loadLabels();
            }}
          />

          {unlabelled.length === 0 ? (
            <div style={{ fontSize: 11, color: "#2a2a2a", padding: "20px 0" }}>
              All events labelled ✓
            </div>
          ) : (
            unlabelled.map((e) => (
              <EventLabeller key={e.id} event={e} onLabelled={handleLabelled} />
            ))
          )}
        </div>
      )}

      {/* ── METRICS tab ───────────────────────────────────────────────────── */}
      {tab === "metrics" && (
        <div>
          {/* Controls */}
          <div
            style={{
              display: "flex",
              gap: 10,
              marginBottom: 16,
              alignItems: "flex-end",
              flexWrap: "wrap",
            }}
          >
            <div>
              <div style={{ fontSize: 9, color: "#444", marginBottom: 3 }}>
                TOTAL MONITORED HOURS (leave blank to auto-estimate)
              </div>
              <input
                type="number"
                placeholder="e.g. 8"
                value={monHours}
                onChange={(e) => setMonHours(e.target.value)}
                style={{
                  width: 100,
                  background: "#111",
                  border: "1px solid #1a1a1a",
                  borderRadius: 4,
                  padding: "5px 8px",
                  color: "#ccc",
                  fontSize: 11,
                }}
              />
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              {["all", "sleeping", "drowsy"].map((t) => (
                <button
                  key={t}
                  onClick={() => setFilterType(t)}
                  style={{
                    background: filterType === t ? "#111" : "transparent",
                    border: `1px solid ${filterType === t ? "#444" : "#1a1a1a"}`,
                    borderRadius: 5,
                    padding: "5px 12px",
                    cursor: "pointer",
                    color: filterType === t ? "#ddd" : "#444",
                    fontSize: 10,
                  }}
                >
                  {t.toUpperCase()}
                </button>
              ))}
            </div>
            <button
              onClick={loadMetrics}
              disabled={loading}
              style={{
                background: "#00bcd418",
                border: "1px solid #00bcd4",
                borderRadius: 6,
                padding: "6px 16px",
                cursor: "pointer",
                color: "#00bcd4",
                fontSize: 10,
                letterSpacing: 1,
              }}
            >
              {loading ? "Computing…" : "Compute Metrics"}
            </button>
          </div>

          {metrics && (
            <>
              {!metrics.enough_data ? (
                <div
                  style={{
                    fontSize: 11,
                    color: "#666",
                    padding: "12px",
                    background: "#0a0a0a",
                    borderRadius: 6,
                    border: "1px solid #1a1a1a",
                  }}
                >
                  ⚠ {metrics.message}
                  <div style={{ fontSize: 10, color: "#333", marginTop: 6 }}>
                    Labels so far: TP={metrics.tp} FP={metrics.fp} FN=
                    {metrics.fn} | Unlabelled events: {metrics.unlabelled_count}
                  </div>
                </div>
              ) : (
                <>
                  {/* Core metric cards */}
                  <div
                    style={{
                      display: "flex",
                      gap: 10,
                      flexWrap: "wrap",
                      marginBottom: 20,
                    }}
                  >
                    <MetricCard
                      label="Precision"
                      value={
                        metrics.precision != null
                          ? `${(metrics.precision * 100).toFixed(1)}%`
                          : "—"
                      }
                      sub={`${metrics.tp} TP / ${metrics.tp + metrics.fp} alerts`}
                      color="#00e676"
                    />
                    <MetricCard
                      label="Recall"
                      value={
                        metrics.recall != null
                          ? `${(metrics.recall * 100).toFixed(1)}%`
                          : "—"
                      }
                      sub={`${metrics.tp} caught / ${metrics.tp + metrics.fn} real`}
                      color="#00bcd4"
                    />
                    <MetricCard
                      label="F1 Score"
                      value={
                        metrics.f1 != null
                          ? `${(metrics.f1 * 100).toFixed(1)}%`
                          : "—"
                      }
                      sub="harmonic mean P+R"
                      color="#69f0ae"
                    />
                    <MetricCard
                      label="FP / Hour"
                      value={
                        metrics.fp_per_hour != null
                          ? metrics.fp_per_hour.toFixed(2)
                          : "—"
                      }
                      sub={`${metrics.monitored_hours.toFixed(1)}h monitored`}
                      color="#ff8c00"
                    />
                    <MetricCard
                      label="Avg Latency"
                      value={
                        metrics.mean_detection_lag != null
                          ? `${metrics.mean_detection_lag.toFixed(1)}s`
                          : "—"
                      }
                      sub={
                        metrics.min_detection_lag != null
                          ? `${metrics.min_detection_lag.toFixed(0)}s–${metrics.max_detection_lag.toFixed(0)}s range`
                          : "no lag data yet"
                      }
                      color="#ff6644"
                    />
                  </div>

                  {/* Progress bars */}
                  <div style={{ marginBottom: 20 }}>
                    <div
                      style={{
                        fontSize: 9,
                        color: "#444",
                        letterSpacing: 2,
                        marginBottom: 10,
                      }}
                    >
                      PERFORMANCE BARS
                    </div>
                    {[
                      {
                        label: "Precision",
                        val: metrics.precision,
                        color: "#00e676",
                      },
                      {
                        label: "Recall",
                        val: metrics.recall,
                        color: "#00bcd4",
                      },
                      { label: "F1", val: metrics.f1, color: "#69f0ae" },
                    ].map((m) => (
                      <div key={m.label} style={{ marginBottom: 8 }}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            fontSize: 10,
                            marginBottom: 3,
                          }}
                        >
                          <span style={{ color: "#555" }}>{m.label}</span>
                          <span style={{ color: m.color }}>
                            {m.val != null
                              ? `${(m.val * 100).toFixed(1)}%`
                              : "—"}
                          </span>
                        </div>
                        <ProgressBar value={m.val} color={m.color} />
                      </div>
                    ))}
                  </div>

                  {/* By fatigue type */}
                  <div style={{ marginBottom: 20 }}>
                    <div
                      style={{
                        fontSize: 9,
                        color: "#444",
                        letterSpacing: 2,
                        marginBottom: 10,
                      }}
                    >
                      BY FATIGUE TYPE
                    </div>
                    <div style={{ display: "flex", gap: 10 }}>
                      {Object.entries(metrics.by_fatigue_type).map(
                        ([ftype, m]) => (
                          <div
                            key={ftype}
                            style={{
                              background: "#0a0a0a",
                              border: "1px solid #1a1a1a",
                              borderRadius: 8,
                              padding: "10px 14px",
                              flex: 1,
                            }}
                          >
                            <div
                              style={{
                                fontSize: 10,
                                color:
                                  ftype === "sleeping" ? "#ff2020" : "#ff8c00",
                                fontWeight: 700,
                                marginBottom: 8,
                              }}
                            >
                              {ftype === "sleeping" ? "😴" : "😪"}{" "}
                              {ftype.toUpperCase()}
                            </div>
                            <div
                              style={{ display: "flex", gap: 12, fontSize: 10 }}
                            >
                              <span style={{ color: "#00e676" }}>
                                P=
                                {m.precision != null
                                  ? `${(m.precision * 100).toFixed(0)}%`
                                  : "—"}
                              </span>
                              <span style={{ color: "#00bcd4" }}>
                                R=
                                {m.recall != null
                                  ? `${(m.recall * 100).toFixed(0)}%`
                                  : "—"}
                              </span>
                              <span style={{ color: "#444" }}>
                                {m.tp}TP {m.fp}FP {m.fn}FN
                              </span>
                            </div>
                          </div>
                        ),
                      )}
                    </div>
                  </div>

                  {/* FP by trigger */}
                  {Object.keys(metrics.by_trigger).length > 0 && (
                    <div>
                      <div
                        style={{
                          fontSize: 9,
                          color: "#ff2020",
                          letterSpacing: 2,
                          marginBottom: 10,
                        }}
                      >
                        FALSE POSITIVE TRIGGERS (what caused wrong alerts)
                      </div>
                      {Object.entries(metrics.by_trigger)
                        .sort(([, a], [, b]) => b - a)
                        .map(([trigger, count]) => (
                          <div
                            key={trigger}
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              fontSize: 10,
                              padding: "4px 0",
                              borderBottom: "1px solid #0d0d0d",
                            }}
                          >
                            <span style={{ color: "#555" }}>{trigger}</span>
                            <span
                              style={{
                                color: "#ff4444",
                                fontFamily: "monospace",
                              }}
                            >
                              {count} FP
                            </span>
                          </div>
                        ))}
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      )}

      {/* ── HISTORY tab ───────────────────────────────────────────────────── */}
      {tab === "history" && (
        <div>
          <div style={{ fontSize: 9, color: "#333", marginBottom: 12 }}>
            {labels.length} total labels · click × to remove a label
          </div>
          {labels.length === 0 ? (
            <div style={{ fontSize: 11, color: "#222" }}>No labels yet.</div>
          ) : (
            labels.map((l) => {
              const cfg = LABEL_CFG[l.label_type] || LABEL_CFG.TP;
              return (
                <div
                  key={l.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "7px 10px",
                    marginBottom: 4,
                    background: "#0a0a0a",
                    border: `1px solid ${cfg.color}22`,
                    borderRadius: 5,
                    fontSize: 10,
                    fontFamily: "monospace",
                  }}
                >
                  <span
                    style={{ color: cfg.color, fontWeight: 700, width: 28 }}
                  >
                    {l.label_type}
                  </span>
                  <span style={{ color: "#555", flex: 1 }}>
                    {l.fatigue_type} · P{l.person_id ?? "?"} ·{" "}
                    {fmt(l.started_at)}
                    {l.event_id ? ` · evt#${l.event_id}` : " · (FN)"}
                  </span>
                  {l.detection_lag != null && (
                    <span style={{ color: "#444", marginRight: 10 }}>
                      lag={l.detection_lag.toFixed(0)}s
                    </span>
                  )}
                  <span style={{ color: "#333", marginRight: 10 }}>
                    {l.labelled_by || ""}
                  </span>
                  <button
                    onClick={() => deleteLabel(l.id)}
                    style={{
                      background: "transparent",
                      border: "none",
                      cursor: "pointer",
                      color: "#2a2a2a",
                      fontSize: 14,
                      padding: "0 4px",
                    }}
                  >
                    ×
                  </button>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
