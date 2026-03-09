import { useEffect, useState, useRef } from "react";
import axios from "axios";

const API = "http://localhost:8000";

const LABELS = [
  {
    key: "sitting",
    icon: "🪑",
    color: "#00bcd4",
    desc: "Person clearly seated at desk",
  },
  {
    key: "standing",
    icon: "🧍",
    color: "#00e676",
    desc: "Person clearly standing upright",
  },
  {
    key: "awake",
    icon: "👁️",
    color: "#69f0ae",
    desc: "Person alert, actively working",
  },
  {
    key: "drowsy",
    icon: "😪",
    color: "#ff8c00",
    desc: "Person visibly drowsy / nodding",
  },
  {
    key: "sleeping",
    icon: "😴",
    color: "#ff2020",
    desc: "Person clearly asleep at desk",
  },
];

// Which signals matter for which label — shown highlighted in the live panel
const RELEVANT_SIGNALS = {
  sitting: ["knee_hip_x_gap", "knee_hip_y_gap", "torso_compactness"],
  standing: ["knee_hip_y_gap", "knee_hip_x_gap", "torso_compactness"],
  awake: ["wrist_activity", "spine_angle", "head_drop_angle"],
  drowsy: ["head_drop_angle", "spine_angle", "shoulder_ear_ratio"],
  sleeping: ["head_drop_angle", "head_tilt_angle", "spine_angle"],
};

function CountBadge({ count, needed = 5 }) {
  const ok = count >= needed;
  return (
    <span
      style={{
        background: ok ? "#00e67622" : "#ff202022",
        border: `1px solid ${ok ? "#00e676" : "#ff2020"}66`,
        borderRadius: 12,
        padding: "1px 10px",
        fontSize: 11,
        fontFamily: "monospace",
        color: ok ? "#00e676" : "#ff6060",
      }}
    >
      {count}/{needed}
    </span>
  );
}

function SignalRow({
  label,
  value,
  unit = "",
  highlight = false,
  thresholdNote = "",
}) {
  if (value == null)
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 10,
          padding: "4px 0",
          borderBottom: "1px solid #0d0d0d",
          fontFamily: "monospace",
        }}
      >
        <span style={{ color: "#2a2a2a" }}>{label}</span>
        <span style={{ color: "#1a1a1a" }}>—</span>
      </div>
    );
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: 10,
        padding: "4px 0",
        borderBottom: "1px solid #0d0d0d",
        fontFamily: "monospace",
        background: highlight ? "#0a1a0a" : "transparent",
        borderRadius: highlight ? 3 : 0,
        padding: highlight ? "4px 6px" : "4px 0",
      }}
    >
      <span style={{ color: highlight ? "#aaa" : "#555" }}>{label}</span>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {thresholdNote && (
          <span style={{ color: "#333", fontSize: 9 }}>{thresholdNote}</span>
        )}
        <span
          style={{
            color: highlight ? "#00e676" : "#666",
            fontWeight: highlight ? 700 : 400,
          }}
        >
          {typeof value === "number" ? value.toFixed(3) : value}
          {unit}
        </span>
      </div>
    </div>
  );
}

export default function Calibration() {
  const [status, setStatus] = useState(null);
  const [livePersons, setLivePersons] = useState({});
  const [selectedLabel, setLabel] = useState("sitting");
  const [selectedPerson, setPerson] = useState(null); // track_id to sample
  const [result, setResult] = useState(null);
  const [capturing, setCapturing] = useState(false);
  const [message, setMessage] = useState("");
  const captureRef = useRef(null);

  // Load calibration status
  useEffect(() => {
    const load = () =>
      axios
        .get(`${API}/calibrate/status`)
        .then((r) => setStatus(r.data))
        .catch(() => {});
    load();
    const iv = setInterval(load, 2000);
    return () => clearInterval(iv);
  }, []);

  // Poll live persons with their signals
  useEffect(() => {
    const load = () =>
      axios
        .get(`${API}/status`)
        .then((r) => {
          setLivePersons(r.data || {});
          // Auto-select first person if none selected
          const ids = Object.keys(r.data || {});
          if (ids.length > 0 && selectedPerson === null) {
            setPerson(parseInt(ids[0]));
          }
        })
        .catch(() => {});
    load();
    const iv = setInterval(load, 600);
    return () => clearInterval(iv);
  }, [selectedPerson]);

  const currentPerson =
    selectedPerson !== null
      ? livePersons[String(selectedPerson)]
      : Object.values(livePersons)[0];

  const relevantKeys = RELEVANT_SIGNALS[selectedLabel] || [];

  const buildSampleSignals = (person) => {
    if (!person) return null;
    const s = person.signals || {};
    return {
      // Posture signals — what the classifier actually uses
      knee_hip_y_gap: s.knee_hip_y_gap,
      knee_hip_x_gap: s.knee_hip_x_gap,
      torso_compactness: s.torso_compactness,
      sh_hip_y_gap: s.sh_hip_y_gap,
      // Fatigue signals
      head_drop_angle: s.head_drop_angle,
      head_tilt_angle: s.head_tilt_angle,
      spine_angle: s.spine_angle,
      shoulder_ear_ratio: s.shoulder_ear_ratio,
      wrist_activity: s.wrist_activity,
      // Context
      recline: person.reclined_ratio,
      inactive_s: person.inactive_seconds,
      current_state: person.state,
    };
  };

  const sendSample = async () => {
    const signals = buildSampleSignals(currentPerson);
    if (!signals) {
      setMessage("⚠ No live person detected");
      return;
    }
    if (signals.knee_hip_y_gap == null && selectedLabel !== "sleeping") {
      setMessage("⚠ Knee signals not visible — make sure knees are in frame");
    }
    try {
      const res = await axios.post(`${API}/calibrate/sample`, {
        label: selectedLabel,
        signals,
        track_id: currentPerson?.track_id ?? null,
      });
      if (res.data.error) {
        setMessage(`⚠ ${res.data.error}`);
        return;
      }
      const cfg = LABELS.find((l) => l.key === selectedLabel);
      setMessage(
        `${cfg.icon} Sample captured for "${selectedLabel}" (P${currentPerson?.track_id})`,
      );
    } catch (e) {
      setMessage(`Error: ${e.message}`);
    }
  };

  const startBurst = () => {
    if (captureRef.current) return;
    setCapturing(true);
    let n = 0;
    setMessage(`Capturing 15 samples for "${selectedLabel}"…`);
    captureRef.current = setInterval(async () => {
      await sendSample();
      n++;
      if (n >= 15) {
        clearInterval(captureRef.current);
        captureRef.current = null;
        setCapturing(false);
        setMessage(`✓ Done — 15 samples captured for "${selectedLabel}"`);
      }
    }, 250);
  };

  const computeThresholds = async () => {
    try {
      setMessage("Computing thresholds from samples…");
      const r = await axios.post(`${API}/calibrate/compute`);
      if (r.data.error) {
        setMessage(`⚠ ${r.data.error}`);
        return;
      }
      setResult(r.data);
      if (r.data.written_to_env) {
        setMessage("✓ Thresholds saved to .env — restart docker to apply.");
      } else {
        setMessage(
          "⚠ Thresholds computed but could not write to .env (check server logs).",
        );
      }
    } catch (e) {
      setMessage(`Error: ${e.message}`);
    }
  };

  const clearAll = async () => {
    await axios.delete(`${API}/calibrate/samples`);
    setResult(null);
    setMessage("Samples cleared.");
  };

  const counts = status?.counts || {};
  const ready = status?.ready || false;
  const cfg = LABELS.find((l) => l.key === selectedLabel);
  const persons = Object.values(livePersons);

  // Current .env threshold values for display
  const envThresholds = {
    POSTURE_STANDING_KNEE_Y_GAP: "standing Y gap threshold",
    POSTURE_SEATED_KNEE_X_GAP: "seated X gap threshold",
    POSTURE_SIT_Y_RATIO: "sit torso ratio",
  };

  return (
    <div style={{ fontFamily: "monospace", color: "#ccc" }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div
          style={{
            fontSize: 11,
            letterSpacing: 4,
            color: "#555",
            textTransform: "uppercase",
            marginBottom: 6,
          }}
        >
          Camera Calibration
        </div>
        <div style={{ fontSize: 10, color: "#2a2a2a", lineHeight: 1.7 }}>
          Teach the detector YOUR camera's exact geometry by labeling real
          people visible in the live feed. The tool measures their actual
          skeleton ratios and computes correct thresholds automatically.
        </div>
      </div>

      {/* How-to */}
      <div
        style={{
          background: "#080808",
          border: "1px solid #0d0d0d",
          borderLeft: "3px solid #00bcd4",
          borderRadius: 8,
          padding: "10px 14px",
          marginBottom: 20,
          fontSize: 10,
          color: "#444",
          lineHeight: 1.9,
        }}
      >
        <span style={{ color: "#00bcd4", fontWeight: 700 }}>
          HOW TO CALIBRATE
        </span>
        <br />
        1. Keep camera running with real people visible.
        <br />
        2. Select the person to sample using the person picker below.
        <br />
        3. Select what posture that person is in.
        <br />
        4. Click <b style={{ color: "#ccc" }}>Capture 15 Samples</b> while they
        hold that posture.
        <br />
        5. Repeat for <b style={{ color: "#ccc" }}>sitting</b> and{" "}
        <b style={{ color: "#ccc" }}>standing</b> at minimum.
        <br />
        6. Click <b style={{ color: "#00e676" }}>Compute & Save</b> → restart
        docker.
      </div>

      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 20 }}
      >
        {/* LEFT */}
        <div>
          {/* Person picker */}
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                fontSize: 9,
                color: "#333",
                letterSpacing: 2,
                marginBottom: 8,
              }}
            >
              SELECT PERSON TO SAMPLE
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {persons.length === 0 ? (
                <span style={{ fontSize: 10, color: "#2a2a2a" }}>
                  No persons detected
                </span>
              ) : (
                persons.map((p) => (
                  <button
                    key={p.track_id}
                    onClick={() => setPerson(p.track_id)}
                    style={{
                      background:
                        selectedPerson === p.track_id ? "#1a1a1a" : "#0a0a0a",
                      border: `1px solid ${selectedPerson === p.track_id ? "#555" : "#1a1a1a"}`,
                      borderRadius: 6,
                      padding: "5px 12px",
                      cursor: "pointer",
                      color: selectedPerson === p.track_id ? "#eee" : "#444",
                      fontSize: 10,
                    }}
                  >
                    P{p.track_id}
                    <span
                      style={{
                        marginLeft: 6,
                        fontSize: 9,
                        color:
                          selectedPerson === p.track_id ? "#888" : "#2a2a2a",
                      }}
                    >
                      {p.state}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Label selector */}
          <div
            style={{
              fontSize: 9,
              color: "#333",
              letterSpacing: 2,
              marginBottom: 8,
            }}
          >
            WHAT POSTURE IS THIS PERSON IN?
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              marginBottom: 16,
            }}
          >
            {LABELS.map((l) => (
              <div
                key={l.key}
                onClick={() => setLabel(l.key)}
                style={{
                  background: selectedLabel === l.key ? "#111" : "#080808",
                  border: `1px solid ${selectedLabel === l.key ? l.color + "88" : "#111"}`,
                  borderLeft: `3px solid ${l.color}`,
                  borderRadius: 6,
                  padding: "8px 12px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <span style={{ fontSize: 18 }}>{l.icon}</span>
                <div style={{ flex: 1 }}>
                  <div
                    style={{ color: l.color, fontSize: 11, fontWeight: 700 }}
                  >
                    {l.key.toUpperCase()}
                  </div>
                  <div style={{ color: "#333", fontSize: 9 }}>{l.desc}</div>
                </div>
                <CountBadge count={counts[l.key] || 0} needed={5} />
              </div>
            ))}
          </div>

          {/* Capture buttons */}
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <button
              onClick={sendSample}
              style={{
                background: "#111",
                border: `1px solid ${cfg?.color}44`,
                borderRadius: 6,
                padding: "7px 16px",
                cursor: "pointer",
                color: cfg?.color,
                fontSize: 10,
                letterSpacing: 1,
              }}
            >
              {cfg?.icon} Capture 1
            </button>
            <button
              onClick={startBurst}
              disabled={capturing}
              style={{
                background: capturing ? "#0a0a0a" : cfg?.color + "18",
                border: `1px solid ${cfg?.color}66`,
                borderRadius: 6,
                padding: "7px 16px",
                cursor: capturing ? "default" : "pointer",
                color: cfg?.color,
                fontSize: 10,
                letterSpacing: 1,
              }}
            >
              {capturing ? "Capturing…" : "⚡ Capture 15 Samples"}
            </button>
          </div>

          {message && (
            <div
              style={{
                fontSize: 10,
                color: "#777",
                background: "#0a0a0a",
                padding: "7px 10px",
                borderRadius: 5,
                border: "1px solid #111",
                marginBottom: 12,
              }}
            >
              {message}
            </div>
          )}

          {/* Compute + clear */}
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={computeThresholds}
              disabled={!ready}
              style={{
                background: ready ? "#00e67614" : "#0a0a0a",
                border: `1px solid ${ready ? "#00e676" : "#1a1a1a"}`,
                borderRadius: 6,
                padding: "9px 18px",
                cursor: ready ? "pointer" : "default",
                color: ready ? "#00e676" : "#2a2a2a",
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: 1,
              }}
            >
              ✓ Compute & Save Thresholds
            </button>
            <button
              onClick={clearAll}
              style={{
                background: "transparent",
                border: "1px solid #1a1a1a",
                borderRadius: 6,
                padding: "9px 14px",
                cursor: "pointer",
                color: "#333",
                fontSize: 10,
              }}
            >
              Clear All
            </button>
          </div>
        </div>

        {/* RIGHT — live signals */}
        <div>
          <div
            style={{
              background: "#060606",
              border: "1px solid #111",
              borderRadius: 8,
              padding: 12,
              marginBottom: 12,
            }}
          >
            <div
              style={{
                fontSize: 9,
                color: "#333",
                letterSpacing: 2,
                marginBottom: 8,
              }}
            >
              LIVE SIGNALS {currentPerson ? `— P${currentPerson.track_id}` : ""}
            </div>

            {currentPerson ? (
              (() => {
                const s = currentPerson.signals || {};
                return (
                  <>
                    <div
                      style={{
                        fontSize: 9,
                        color: "#00e676",
                        letterSpacing: 1,
                        marginBottom: 4,
                        marginTop: 8,
                      }}
                    >
                      POSTURE SIGNALS
                    </div>
                    <SignalRow
                      label="knee Y gap (standing↑)"
                      value={s.knee_hip_y_gap}
                      highlight={relevantKeys.includes("knee_hip_y_gap")}
                      thresholdNote="thresh: 0.12"
                    />
                    <SignalRow
                      label="knee X gap (seated↑)"
                      value={s.knee_hip_x_gap}
                      highlight={relevantKeys.includes("knee_hip_x_gap")}
                      thresholdNote="thresh: 0.06"
                    />
                    <SignalRow
                      label="torso compactness"
                      value={s.torso_compactness}
                      highlight={relevantKeys.includes("torso_compactness")}
                      thresholdNote="sit<0.20"
                    />

                    <div
                      style={{
                        fontSize: 9,
                        color: "#ff8c00",
                        letterSpacing: 1,
                        marginBottom: 4,
                        marginTop: 8,
                      }}
                    >
                      FATIGUE SIGNALS
                    </div>
                    <SignalRow
                      label="head drop°"
                      value={s.head_drop_angle}
                      unit="°"
                      highlight={relevantKeys.includes("head_drop_angle")}
                    />
                    <SignalRow
                      label="head tilt°"
                      value={s.head_tilt_angle}
                      unit="°"
                      highlight={relevantKeys.includes("head_tilt_angle")}
                    />
                    <SignalRow
                      label="spine angle°"
                      value={s.spine_angle}
                      unit="°"
                      highlight={relevantKeys.includes("spine_angle")}
                    />
                    <SignalRow
                      label="wrist activity"
                      value={s.wrist_activity}
                      highlight={relevantKeys.includes("wrist_activity")}
                    />

                    <div
                      style={{
                        fontSize: 9,
                        color: "#555",
                        letterSpacing: 1,
                        marginBottom: 4,
                        marginTop: 8,
                      }}
                    >
                      CONTEXT
                    </div>
                    <SignalRow
                      label="current state"
                      value={currentPerson.state?.toUpperCase()}
                    />
                    <SignalRow
                      label="inactive"
                      value={currentPerson.inactive_seconds}
                      unit="s"
                    />
                    <SignalRow
                      label="recline"
                      value={currentPerson.reclined_ratio}
                    />
                  </>
                );
              })()
            ) : (
              <div style={{ fontSize: 10, color: "#222" }}>
                Waiting for live data…
              </div>
            )}
          </div>

          {/* Computed thresholds */}
          {result && (
            <div
              style={{
                background: "#050f05",
                border: "1px solid #00e67622",
                borderRadius: 8,
                padding: 12,
              }}
            >
              <div
                style={{
                  fontSize: 9,
                  color: "#00e676",
                  letterSpacing: 2,
                  marginBottom: 8,
                }}
              >
                COMPUTED THRESHOLDS
              </div>
              {Object.entries(result.thresholds).map(([k, v]) => (
                <div
                  key={k}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    padding: "3px 0",
                    borderBottom: "1px solid #0d0d0d",
                    fontFamily: "monospace",
                  }}
                >
                  <span style={{ color: "#444" }}>{k}</span>
                  <span style={{ color: "#00e676" }}>{v}</span>
                </div>
              ))}
              <div
                style={{
                  fontSize: 9,
                  color: "#444",
                  marginTop: 8,
                  lineHeight: 1.6,
                }}
              >
                {result.written_to_env
                  ? "✓ Written to .env — run docker compose up --build to apply"
                  : "⚠ Could not write .env — copy values manually"}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
