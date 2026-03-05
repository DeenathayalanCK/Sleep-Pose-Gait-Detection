import { useEffect, useState } from "react";
import { getStatus } from "../api";

const STATE_CFG = {
  sleeping: { bg: "#1a0000", accent: "#ff2020", icon: "😴", label: "SLEEPING" },
  drowsy: { bg: "#1a0e00", accent: "#ff8c00", icon: "😪", label: "DROWSY" },
  inactive: { bg: "#0e0e1a", accent: "#7b68ee", icon: "💤", label: "INACTIVE" },
  sitting: { bg: "#001020", accent: "#00bcd4", icon: "🪑", label: "SITTING" },
  standing: { bg: "#001a08", accent: "#00e676", icon: "🧍", label: "STANDING" },
  walking: { bg: "#001a08", accent: "#69f0ae", icon: "🚶", label: "WALKING" },
  awake: { bg: "#001a08", accent: "#00e676", icon: "👁️", label: "AWAKE" },
  no_person: { bg: "#111", accent: "#444", icon: "👻", label: "NO PERSON" },
  unknown: { bg: "#111", accent: "#333", icon: "—", label: "—" },
  starting: { bg: "#111", accent: "#333", icon: "⏳", label: "STARTING" },
};

function Gauge({ label, value, max, unit, accent }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ marginBottom: 14 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 10,
          letterSpacing: 2,
          color: "#555",
          marginBottom: 5,
          textTransform: "uppercase",
        }}
      >
        <span>{label}</span>
        <span style={{ color: accent }}>
          {typeof value === "number" ? value.toFixed(1) : value}
          {unit}
        </span>
      </div>
      <div style={{ height: 3, background: "#1e1e1e", borderRadius: 2 }}>
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: accent,
            borderRadius: 2,
            transition: "width 0.5s ease",
          }}
        />
      </div>
    </div>
  );
}

function Pill({ label, on, accent }) {
  return (
    <span
      style={{
        fontSize: 10,
        letterSpacing: 2,
        padding: "3px 9px",
        borderRadius: 20,
        fontFamily: "monospace",
        textTransform: "uppercase",
        background: on ? `${accent}22` : "#111",
        color: on ? accent : "#333",
        border: `1px solid ${on ? accent + "55" : "#222"}`,
      }}
    >
      {label}
    </span>
  );
}

export default function LiveStatus() {
  const [s, setS] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = () =>
      getStatus()
        .then((r) => {
          setS(r.data);
          setError(null);
        })
        .catch((e) => setError(String(e)));
    load();
    const iv = setInterval(load, 800);
    return () => clearInterval(iv);
  }, []);

  const cfg = STATE_CFG[s?.state] ?? STATE_CFG.unknown;

  return (
    <div
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.accent}33`,
        borderRadius: 12,
        padding: "24px 28px",
        transition: "background 0.5s ease, border-color 0.5s ease",
        boxShadow: `0 0 32px ${cfg.accent}14`,
      }}
    >
      {/* State header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 24,
        }}
      >
        <div
          style={{
            width: 12,
            height: 12,
            borderRadius: "50%",
            background: cfg.accent,
            boxShadow: `0 0 10px ${cfg.accent}`,
            flexShrink: 0,
            animation: s?.state === "sleeping" ? "pulse 1.2s infinite" : "none",
          }}
        />
        <span
          style={{
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: 4,
            color: cfg.accent,
            fontFamily: "monospace",
          }}
        >
          {cfg.icon} {cfg.label}
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 10,
            color: "#333",
            fontFamily: "monospace",
          }}
        >
          {s?.updated_at ? new Date(s.updated_at).toLocaleTimeString() : "—"}
        </span>
      </div>

      {error && (
        <p style={{ color: "#ff4444", fontSize: 11, marginBottom: 12 }}>
          ⚠ {error}
        </p>
      )}

      {s && (
        <>
          <Gauge
            label="Inactive"
            value={s.inactive_seconds}
            max={30}
            unit="s"
            accent={cfg.accent}
          />
          <Gauge
            label="Reclined"
            value={Math.round(s.reclined_ratio * 100)}
            max={100}
            unit="%"
            accent={cfg.accent}
          />
          <Gauge
            label="Motion"
            value={s.motion_score}
            max={10}
            unit=""
            accent={cfg.accent}
          />
          <Gauge
            label="Confidence"
            value={Math.round(s.confidence * 100)}
            max={100}
            unit="%"
            accent={cfg.accent}
          />

          <div
            style={{
              display: "flex",
              gap: 10,
              marginTop: 18,
              flexWrap: "wrap",
            }}
          >
            <Pill label="Pose" on={s.pose_visible} accent={cfg.accent} />
            {s.ear !== null && (
              <Pill label={`EAR ${s.ear}`} on={s.ear < 0.25} accent="#ff8c00" />
            )}
          </div>
        </>
      )}

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.2} }
      `}</style>
    </div>
  );
}
