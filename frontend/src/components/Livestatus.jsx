import { useEffect, useState } from "react";
import { getStatus } from "../api";

const STATE_COLORS = {
  sleeping: { bg: "#1a0000", accent: "#ff2020", label: "SLEEPING" },
  drowsy: { bg: "#1a0e00", accent: "#ff8c00", label: "DROWSY" },
  inactive: { bg: "#0e0e1a", accent: "#7b68ee", label: "INACTIVE" },
  awake: { bg: "#001a08", accent: "#00e676", label: "AWAKE" },
  no_person: { bg: "#111", accent: "#555", label: "NO PERSON" },
  unknown: { bg: "#111", accent: "#555", label: "—" },
  starting: { bg: "#111", accent: "#555", label: "STARTING" },
};

function Gauge({ label, value, max, unit, accent }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ marginBottom: 14 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 11,
          letterSpacing: 2,
          color: "#888",
          marginBottom: 5,
          textTransform: "uppercase",
        }}
      >
        <span>{label}</span>
        <span style={{ color: accent }}>
          {value}
          {unit}
        </span>
      </div>
      <div style={{ height: 4, background: "#222", borderRadius: 2 }}>
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: accent,
            borderRadius: 2,
            transition: "width 0.4s ease",
          }}
        />
      </div>
    </div>
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

  const theme = STATE_COLORS[s?.state] ?? STATE_COLORS.unknown;

  return (
    <div
      style={{
        background: theme.bg,
        border: `1px solid ${theme.accent}33`,
        borderRadius: 12,
        padding: "28px 32px",
        marginBottom: 32,
        transition: "background 0.6s ease",
        boxShadow: `0 0 40px ${theme.accent}18`,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          marginBottom: 24,
        }}
      >
        <div
          style={{
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: theme.accent,
            boxShadow: `0 0 12px ${theme.accent}`,
            animation: s?.state === "sleeping" ? "pulse 1.2s infinite" : "none",
          }}
        />
        <span
          style={{
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: 4,
            color: theme.accent,
            fontFamily: "monospace",
          }}
        >
          {theme.label}
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 11,
            color: "#555",
            fontFamily: "monospace",
          }}
        >
          {s?.updated_at ? new Date(s.updated_at).toLocaleTimeString() : "—"}
        </span>
      </div>

      {error && (
        <p style={{ color: "#ff4444", fontSize: 12, marginBottom: 16 }}>
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
            accent={theme.accent}
          />
          <Gauge
            label="Reclined"
            value={Math.round(s.reclined_ratio * 100)}
            max={100}
            unit="%"
            accent={theme.accent}
          />
          <Gauge
            label="Motion"
            value={s.motion_score}
            max={10}
            unit=""
            accent={theme.accent}
          />
          <Gauge
            label="Confidence"
            value={Math.round(s.confidence * 100)}
            max={100}
            unit="%"
            accent={theme.accent}
          />

          <div style={{ display: "flex", gap: 24, marginTop: 20 }}>
            <Pill label="Pose" on={s.pose_visible} accent={theme.accent} />
            {s.ear !== null && (
              <Pill label={`EAR ${s.ear}`} on={s.ear < 0.25} accent="#ff8c00" />
            )}
          </div>
        </>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}

function Pill({ label, on, accent }) {
  return (
    <span
      style={{
        fontSize: 11,
        letterSpacing: 2,
        padding: "4px 10px",
        borderRadius: 20,
        fontFamily: "monospace",
        textTransform: "uppercase",
        background: on ? `${accent}22` : "#1a1a1a",
        color: on ? accent : "#444",
        border: `1px solid ${on ? accent + "44" : "#333"}`,
      }}
    >
      {label}
    </span>
  );
}
