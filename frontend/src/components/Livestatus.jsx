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

function PersonCard({ p }) {
  const cfg = STATE_CFG[p.state] ?? STATE_CFG.unknown;
  const accent = cfg.accent;
  const isAlert = [
    "sleeping",
    "drowsy",
    "sitting_inactive",
    "standing_inactive",
  ].includes(p.state);

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
      </div>
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
