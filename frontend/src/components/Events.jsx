import { useEffect, useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

function imgUrl(path) {
  if (!path) return null;
  return `${API}/snapshots/${path.split(/[\\/]/).pop()}`;
}

function fmt(iso) {
  return iso ? iso.replace("T", " ").slice(0, 19) : "—";
}

// Visual config per fatigue type
const TYPE_CFG = {
  sleeping: {
    accent: "#ff2020",
    label: "SLEEPING",
    icon: "😴",
    border: "#ff202044",
  },
  drowsy: {
    accent: "#ff8c00",
    label: "DROWSY",
    icon: "😪",
    border: "#ff8c0044",
  },
};

function TypeBadge({ type }) {
  const cfg = TYPE_CFG[type] ?? TYPE_CFG.sleeping;
  return (
    <span
      style={{
        background: cfg.accent + "22",
        border: `1px solid ${cfg.accent}66`,
        borderRadius: 5,
        padding: "3px 10px",
        fontSize: 10,
        fontFamily: "monospace",
        color: cfg.accent,
        fontWeight: 700,
        letterSpacing: 2,
      }}
    >
      {cfg.icon} {cfg.label}
    </span>
  );
}

function CauseBanner({ cause }) {
  if (!cause) return null;
  return (
    <div
      style={{
        background: "#0f0a00",
        border: "1px solid #ff8c0022",
        borderLeft: "3px solid #ff8c00",
        borderRadius: 6,
        padding: "7px 12px",
        marginBottom: 10,
        fontSize: 11,
        color: "#cc8800",
        fontFamily: "monospace",
        lineHeight: 1.5,
      }}
    >
      <span
        style={{ color: "#ccc", marginRight: 8, fontSize: 9, letterSpacing: 2 }}
      >
        WHY
      </span>
      {cause}
    </div>
  );
}

function Badge({ label, value, accent }) {
  return (
    <div
      style={{
        background: "#111",
        border: `1px solid ${accent}33`,
        borderRadius: 6,
        padding: "5px 10px",
        minWidth: 72,
      }}
    >
      <div
        style={{
          fontSize: 9,
          letterSpacing: 2,
          color: "#bbb",
          textTransform: "uppercase",
          marginBottom: 2,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 13,
          color: accent,
          fontFamily: "monospace",
          fontWeight: 700,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function EventCard({ e }) {
  const [showFull, setShowFull] = useState(false);
  const cfg = TYPE_CFG[e.fatigue_type] ?? TYPE_CFG.sleeping;
  const accent = cfg.accent;
  const cropUrl = imgUrl(e.crop_snapshot);
  const fullUrl = imgUrl(e.snapshot);

  return (
    <div
      style={{
        background: "#0d0d0d",
        border: `1px solid ${cfg.border}`,
        borderLeft: `3px solid ${accent}`,
        borderRadius: 8,
        padding: 18,
        display: "grid",
        gridTemplateColumns: "120px 1fr",
        gap: 18,
      }}
    >
      {/* ── Left: crop + full scene ─────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ position: "relative" }}>
          {cropUrl ? (
            <img
              src={cropUrl}
              alt={`P${e.person_id}`}
              style={{
                width: 120,
                height: 165,
                objectFit: "cover",
                borderRadius: 6,
                border: `2px solid ${accent}44`,
                display: "block",
              }}
            />
          ) : (
            <div
              style={{
                width: 120,
                height: 165,
                background: "#1a1a1a",
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexDirection: "column",
                gap: 6,
                border: "1px solid #2a2a2a",
              }}
            >
              <span style={{ fontSize: 28 }}>{cfg.icon}</span>
              <span style={{ fontSize: 9, color: "#333", letterSpacing: 1 }}>
                NO CROP
              </span>
            </div>
          )}
          {/* Person ID overlay */}
          <div
            style={{
              position: "absolute",
              bottom: 6,
              left: 6,
              background: "#000000aa",
              border: `1px solid ${accent}66`,
              borderRadius: 4,
              padding: "2px 7px",
              fontFamily: "monospace",
              fontSize: 11,
              color: accent,
              fontWeight: 700,
            }}
          >
            P{e.person_id ?? "?"}
          </div>
        </div>

        {/* Full scene thumbnail */}
        {fullUrl && (
          <div
            onMouseEnter={() => setShowFull(true)}
            onMouseLeave={() => setShowFull(false)}
            style={{ position: "relative", cursor: "pointer" }}
          >
            <img
              src={fullUrl}
              style={{
                width: 120,
                height: 68,
                objectFit: "cover",
                borderRadius: 4,
                border: "1px solid #2a2a2a",
                opacity: 0.55,
                display: "block",
              }}
              alt="room"
            />
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 9,
                color: "#ccc",
                letterSpacing: 1,
              }}
            >
              FULL SCENE
            </div>

            {showFull && (
              <div
                style={{
                  position: "fixed",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%,-50%)",
                  zIndex: 1000,
                  background: "#000",
                  border: `1px solid ${accent}44`,
                  borderRadius: 8,
                  padding: 8,
                  boxShadow: "0 0 60px #000e",
                }}
              >
                <img
                  src={fullUrl}
                  style={{
                    maxWidth: "80vw",
                    maxHeight: "80vh",
                    borderRadius: 4,
                    display: "block",
                  }}
                  alt="full scene"
                />
                <div
                  style={{
                    fontSize: 10,
                    color: "#bbb",
                    textAlign: "center",
                    marginTop: 6,
                    fontFamily: "monospace",
                  }}
                >
                  #{e.id} · P{e.person_id ?? "?"} · {e.camera_id}
                </div>
              </div>
            )}
          </div>
        )}

        <div
          style={{
            fontSize: 9,
            color: "#2a2a2a",
            fontFamily: "monospace",
            textAlign: "center",
          }}
        >
          #{e.id} · {e.camera_id}
        </div>
      </div>

      {/* ── Right: type + cause + metrics + summary ──────────────── */}
      <div>
        {/* Type badge + timestamps */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 10,
            flexWrap: "wrap",
          }}
        >
          <TypeBadge type={e.fatigue_type} />
          <span
            style={{ fontSize: 10, color: "#bbb", fontFamily: "monospace" }}
          >
            {fmt(e.started_at)} → {e.ended_at ? fmt(e.ended_at) : "ongoing…"}
          </span>
        </div>

        {/* Why this record was created */}
        <CauseBanner cause={e.fatigue_cause} />

        {/* Metric badges */}
        <div
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            marginBottom: 12,
          }}
        >
          <Badge
            label="Person"
            value={`P${e.person_id ?? "?"}`}
            accent="#00bcd4"
          />
          <Badge
            label="Duration"
            value={`${(e.duration || 0).toFixed(1)}s`}
            accent={accent}
          />
          <Badge
            label="Inactive"
            value={`${(e.inactive_seconds || 0).toFixed(1)}s`}
            accent="#ff6644"
          />
          <Badge
            label="Reclined"
            value={`${((e.reclined_ratio || 0) * 100).toFixed(0)}%`}
            accent="#ff8844"
          />
          <Badge
            label="Confidence"
            value={`${((e.confidence || 0) * 100).toFixed(0)}%`}
            accent="#ffaa44"
          />
          <Badge label="Trigger" value={e.trigger || "—"} accent="#aaa" />
        </div>

        {/* LLM summary */}
        <div
          style={{
            fontSize: 11,
            color: "#ccc",
            lineHeight: 1.7,
            fontFamily: "monospace",
            borderTop: "1px solid #1a1a1a",
            paddingTop: 10,
          }}
        >
          {e.summary ? (
            e.summary
          ) : (
            <span style={{ color: "#2a2a2a" }}>Generating summary…</span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Events() {
  const [events, setEvents] = useState([]);
  const [filter, setFilter] = useState("all"); // "all" | "sleeping" | "drowsy"
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = () =>
      axios
        .get(`${API}/fatigue-events`)
        .then((r) => {
          setEvents(r.data);
          setError(null);
        })
        .catch((e) => setError(String(e)));
    load();
    const iv = setInterval(load, 4000);
    return () => clearInterval(iv);
  }, []);

  const visible =
    filter === "all" ? events : events.filter((e) => e.fatigue_type === filter);

  const nSleep = events.filter((e) => e.fatigue_type === "sleeping").length;
  const nDrowsy = events.filter((e) => e.fatigue_type === "drowsy").length;

  return (
    <div>
      {/* Header + filter tabs */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 16,
          flexWrap: "wrap",
        }}
      >
        <h2
          style={{
            fontSize: 11,
            letterSpacing: 4,
            color: "#ccc",
            textTransform: "uppercase",
            margin: 0,
          }}
        >
          Fatigue Records
        </h2>

        {/* Filter tabs */}
        {[
          { key: "all", label: `ALL  ${events.length}` },
          { key: "sleeping", label: `😴 SLEEPING  ${nSleep}` },
          { key: "drowsy", label: `😪 DROWSY  ${nDrowsy}` },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            style={{
              background: filter === tab.key ? "#1a1a1a" : "transparent",
              border: `1px solid ${filter === tab.key ? "#444" : "#222"}`,
              borderRadius: 6,
              padding: "4px 12px",
              color: filter === tab.key ? "#fff" : "#aaa",
              fontSize: 10,
              fontFamily: "monospace",
              letterSpacing: 1,
              cursor: "pointer",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <p style={{ color: "#f44", fontSize: 12 }}>⚠ {error}</p>}

      {visible.length === 0 ? (
        <p style={{ color: "#2a2a2a", fontSize: 12, fontFamily: "monospace" }}>
          No {filter === "all" ? "" : filter + " "}records yet.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {visible.map((e) => (
            <EventCard key={e.id} e={e} />
          ))}
        </div>
      )}
    </div>
  );
}
