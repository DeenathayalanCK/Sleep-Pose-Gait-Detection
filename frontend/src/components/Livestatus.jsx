import { useEffect, useState } from "react";
import { getStatus } from "../api";

const STATE_CFG = {
  sleeping: { accent: "#ff2020", icon: "😴", label: "SLEEPING" },
  drowsy: { accent: "#ff8c00", icon: "😪", label: "DROWSY" },
  sitting_inactive: { accent: "#9c6fef", icon: "💤", label: "SITTING (IDLE)" },
  standing_inactive: {
    accent: "#8060cc",
    icon: "💤",
    label: "STANDING (IDLE)",
  },
  inactive: { accent: "#7b68ee", icon: "💤", label: "INACTIVE" },
  sitting: { accent: "#00bcd4", icon: "🪑", label: "SITTING" },
  standing: { accent: "#00e676", icon: "🧍", label: "STANDING" },
  walking: { accent: "#69f0ae", icon: "🚶", label: "WALKING" },
  awake: { accent: "#00e676", icon: "👁️", label: "AWAKE" },
  no_person: { accent: "#333", icon: "👻", label: "NO PERSON" },
  unknown: { accent: "#2a2a2a", icon: "—", label: "UNKNOWN" },
};

const STATE_PRIORITY = [
  "sleeping",
  "drowsy",
  "sitting_inactive",
  "standing_inactive",
  "sitting",
  "standing",
  "walking",
  "awake",
  "inactive",
  "unknown",
  "no_person",
];

// Z-score bar: shows how far a signal deviates from personal baseline
// Green < 1σ, yellow 1–2σ, orange 2–3σ, red > 3σ
function ZBar({ label, z }) {
  if (z == null) return null;
  const abs = Math.abs(z);
  const pct = Math.min(100, (abs / 4) * 100); // 4σ = full bar
  const color =
    abs >= 3
      ? "#ff2020"
      : abs >= 2
        ? "#ff8c00"
        : abs >= 1
          ? "#ffcc00"
          : "#00e676";
  return (
    <div style={{ marginBottom: 3 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 9,
          color: "#444",
          marginBottom: 2,
        }}
      >
        <span>{label}</span>
        <span style={{ color, fontFamily: "monospace" }}>
          {z > 0 ? "+" : ""}
          {z.toFixed(1)}σ
        </span>
      </div>
      <div
        style={{
          background: "#111",
          borderRadius: 3,
          height: 4,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: 3,
            transition: "width 0.4s, background 0.4s",
          }}
        />
      </div>
    </div>
  );
}

// Warmup progress ring — shows how many awake samples collected vs needed (150)
function WarmupRing({ samples, needed = 150 }) {
  const pct = Math.min(1, samples / needed);
  const radius = 14;
  const circ = 2 * Math.PI * radius;
  const dash = pct * circ;
  const ready = pct >= 1;
  const color = ready ? "#00e676" : "#ff8c00";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <svg width={34} height={34} style={{ flexShrink: 0 }}>
        {/* Track */}
        <circle
          cx={17}
          cy={17}
          r={radius}
          fill="none"
          stroke="#1a1a1a"
          strokeWidth={3}
        />
        {/* Progress */}
        <circle
          cx={17}
          cy={17}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={3}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 17 17)"
          style={{ transition: "stroke-dasharray 0.6s" }}
        />
        {/* Percentage */}
        <text
          x={17}
          y={21}
          textAnchor="middle"
          style={{
            fontSize: 8,
            fill: color,
            fontFamily: "monospace",
            fontWeight: 700,
          }}
        >
          {Math.round(pct * 100)}%
        </text>
      </svg>
      <div>
        <div
          style={{
            fontSize: 9,
            color,
            fontFamily: "monospace",
            fontWeight: 700,
            letterSpacing: 1,
          }}
        >
          {ready ? "BASELINE READY" : "LEARNING…"}
        </div>
        <div style={{ fontSize: 9, color: "#333", fontFamily: "monospace" }}>
          {samples}/{needed} awake frames
        </div>
      </div>
    </div>
  );
}

function ZScorePanel({ p }) {
  const ready = p.z_baseline_ready;
  const samples = p.z_samples || 0;
  const maxZ = p.z_max;
  const triggered = p.z_triggered;
  const scores = p.z_scores || {};

  // Signal display names
  const SIG_LABELS = {
    head_drop_angle: "Head drop",
    spine_angle: "Spine angle",
    head_tilt_angle: "Head tilt",
    shoulder_ear_ratio: "Shoulder/ear",
    wrist_activity: "Wrist activity",
  };

  return (
    <div style={{ marginTop: 10, borderTop: "1px solid #111", paddingTop: 9 }}>
      {/* Header row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <span style={{ fontSize: 9, color: "#333", letterSpacing: 2 }}>
          Z-SCORE BASELINE
        </span>
        {ready && maxZ != null && (
          <span
            style={{
              fontSize: 9,
              fontFamily: "monospace",
              color: maxZ >= 3 ? "#ff2020" : maxZ >= 2 ? "#ff8c00" : "#444",
              fontWeight: maxZ >= 2 ? 700 : 400,
            }}
          >
            peak {maxZ >= 0 ? "+" : ""}
            {maxZ.toFixed(1)}σ
            {triggered
              ? ` (${triggered.replace("_angle", "").replace("_", " ")})`
              : ""}
          </span>
        )}
      </div>

      {/* Warmup ring */}
      <div style={{ marginBottom: ready ? 10 : 0 }}>
        <WarmupRing samples={samples} needed={150} />
      </div>

      {/* Signal bars — only shown once baseline is ready */}
      {ready && Object.keys(scores).length > 0 && (
        <div style={{ marginTop: 8 }}>
          {Object.entries(scores).map(([key, z]) => (
            <ZBar key={key} label={SIG_LABELS[key] || key} z={z} />
          ))}
          {/* What the z-score means right now */}
          <div
            style={{
              marginTop: 6,
              fontSize: 9,
              color: "#2a2a2a",
              fontFamily: "monospace",
              lineHeight: 1.7,
            }}
          >
            {maxZ >= 3 ? (
              <span style={{ color: "#ff2020" }}>
                ⚠ {triggered?.replace("_angle", "") || "signal"} is{" "}
                {maxZ.toFixed(1)}σ above this person's normal — anomalous for
                them specifically
              </span>
            ) : maxZ >= 2 ? (
              <span style={{ color: "#ff8c00" }}>
                {triggered?.replace("_angle", "") || "signal"} elevated{" "}
                {maxZ.toFixed(1)}σ above personal baseline
              </span>
            ) : (
              <span style={{ color: "#2a2a2a" }}>
                Within personal normal range
              </span>
            )}
          </div>
        </div>
      )}

      {/* Explanation when still warming up */}
      {!ready && (
        <div
          style={{
            fontSize: 9,
            color: "#222",
            marginTop: 6,
            fontFamily: "monospace",
            lineHeight: 1.7,
          }}
        >
          Watching this person's normal posture.
          <br />
          Baseline activates after {150 - samples} more awake frames.
          <br />
          <span style={{ color: "#1a1a1a" }}>
            Only updates while person is actively working (wrist moving, not
            reclined, not idle).
          </span>
        </div>
      )}
    </div>
  );
}

function PersonCard({ p }) {
  const cfg = STATE_CFG[p.state] ?? STATE_CFG.unknown;
  const accent = cfg.accent;
  const isAlert = [
    "sleeping",
    "drowsy",
    "sitting_inactive",
    "standing_inactive",
  ].includes(p.state);
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        background: isAlert ? "#100808" : "#0a0a0a",
        border: `1px solid ${accent}44`,
        borderLeft: `3px solid ${accent}`,
        borderRadius: 8,
        padding: "10px 14px",
        marginBottom: 8,
        boxShadow: isAlert ? `0 0 14px ${accent}22` : "none",
        transition: "all 0.4s ease",
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 5,
        }}
      >
        <span style={{ fontSize: 18 }}>{cfg.icon}</span>
        <span
          style={{
            fontFamily: "monospace",
            fontSize: 12,
            color: accent,
            fontWeight: 700,
          }}
        >
          P{p.track_id}
        </span>
        <span
          style={{
            fontFamily: "monospace",
            fontSize: 11,
            color: accent,
            letterSpacing: 2,
            marginLeft: 4,
          }}
        >
          {cfg.label}
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontFamily: "monospace",
            fontSize: 11,
            color: accent,
          }}
        >
          {Math.round(p.confidence * 100)}%
        </span>
      </div>

      {/* Signal row */}
      <div
        style={{
          display: "flex",
          gap: 16,
          fontSize: 10,
          color: "#444",
          fontFamily: "monospace",
        }}
      >
        <span style={{ color: p.inactive_seconds >= 5 ? accent : "#444" }}>
          idle {p.inactive_seconds?.toFixed(1)}s
        </span>
        <span>recline {Math.round((p.reclined_ratio || 0) * 100)}%</span>
        <span>motion {p.motion_score?.toFixed(1)}</span>
        {p.pose_visible && <span style={{ color: "#0f0" }}>● POSE</span>}

        {/* Z-score quick badge */}
        {p.z_baseline_ready ? (
          <span
            style={{
              marginLeft: "auto",
              color:
                p.z_max >= 3 ? "#ff2020" : p.z_max >= 2 ? "#ff8c00" : "#1a1a1a",
              fontWeight: 700,
            }}
          >
            z=
            {p.z_max != null
              ? (p.z_max >= 0 ? "+" : "") + p.z_max.toFixed(1)
              : "—"}
            σ
          </span>
        ) : (
          <span style={{ marginLeft: "auto", color: "#1a1a1a" }}>
            z={p.z_samples || 0}/150
          </span>
        )}
      </div>

      {/* Expand toggle */}
      <button
        onClick={() => setExpanded((e) => !e)}
        style={{
          background: "transparent",
          border: "none",
          cursor: "pointer",
          color: "#2a2a2a",
          fontSize: 9,
          fontFamily: "monospace",
          padding: "4px 0 0 0",
          letterSpacing: 1,
          display: "block",
          width: "100%",
          textAlign: "left",
        }}
      >
        {expanded ? "▲ less" : "▼ z-score detail"}
      </button>

      {expanded && <ZScorePanel p={p} />}
    </div>
  );
}

export default function LiveStatus() {
  const [persons, setPersons] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = () =>
      getStatus()
        .then((r) => {
          setPersons(r.data || {});
          setError(null);
        })
        .catch((e) => setError(String(e)));
    load();
    const iv = setInterval(load, 800);
    return () => clearInterval(iv);
  }, []);

  const list = Object.values(persons);
  const nSleep = list.filter((p) => p.state === "sleeping").length;
  const nIdle = list.filter((p) => p.state?.includes("inactive")).length;
  const nReady = list.filter((p) => p.z_baseline_ready).length;
  const accent = nSleep > 0 ? "#ff2020" : nIdle > 0 ? "#9c6fef" : "#00bcd4";

  const sorted = [...list].sort((a, b) => {
    const ai = STATE_PRIORITY.indexOf(a.state);
    const bi = STATE_PRIORITY.indexOf(b.state);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  return (
    <div
      style={{
        background: "#0a0a0a",
        border: `1px solid ${accent}33`,
        borderRadius: 12,
        padding: "20px 22px",
        boxShadow: nSleep > 0 ? `0 0 24px ${accent}18` : "none",
        transition: "all 0.5s ease",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 16,
        }}
      >
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: accent,
            animation: nSleep > 0 ? "pulse 1.2s infinite" : "none",
          }}
        />
        <span
          style={{
            fontSize: 11,
            letterSpacing: 3,
            color: accent,
            fontFamily: "monospace",
          }}
        >
          {list.length} PERSON{list.length !== 1 ? "S" : ""}
          {nSleep > 0 && (
            <span style={{ color: "#ff2020" }}> ⚠ {nSleep} SLEEPING</span>
          )}
          {nIdle > 0 && (
            <span style={{ color: "#9c6fef" }}> 💤 {nIdle} IDLE</span>
          )}
        </span>
        {/* Z-score readiness indicator */}
        {list.length > 0 && (
          <span
            style={{
              marginLeft: "auto",
              fontSize: 9,
              color: nReady === list.length ? "#00e676" : "#ff8c00",
              fontFamily: "monospace",
            }}
          >
            z:{nReady}/{list.length} ready
          </span>
        )}
      </div>

      {error && <p style={{ color: "#f44", fontSize: 11 }}>⚠ {error}</p>}

      {list.length === 0 ? (
        <p style={{ color: "#222", fontSize: 12, fontFamily: "monospace" }}>
          No persons detected
        </p>
      ) : (
        sorted.map((p) => <PersonCard key={p.track_id} p={p} />)
      )}

      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.2}}`}</style>
    </div>
  );
}
