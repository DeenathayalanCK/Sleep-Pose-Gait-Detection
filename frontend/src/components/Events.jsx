import { useEffect, useState } from "react";
import { getEvents } from "../api";

function snapshotUrl(path) {
  if (!path) return null;
  return `http://localhost:8000/snapshots/${path.split("/").pop()}`;
}

function fmt(iso) {
  if (!iso) return "—";
  return iso.replace("T", " ").slice(0, 19);
}

function Badge({ label, value, accent }) {
  return (
    <div
      style={{
        background: "#111",
        border: `1px solid ${accent}33`,
        borderRadius: 6,
        padding: "6px 10px",
        minWidth: 80,
      }}
    >
      <div
        style={{
          fontSize: 9,
          letterSpacing: 2,
          color: "#444",
          textTransform: "uppercase",
          marginBottom: 3,
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
  const accent = "#ff2020";
  const img = snapshotUrl(e.snapshot);

  return (
    <div
      style={{
        background: "#0d0d0d",
        border: "1px solid #1c1c1c",
        borderLeft: `3px solid ${accent}`,
        borderRadius: 8,
        padding: 20,
        display: "grid",
        gridTemplateColumns: "100px 1fr",
        gap: 20,
      }}
    >
      {/* Keyframe */}
      <div>
        {img ? (
          <img
            src={img}
            style={{
              width: 100,
              height: 70,
              objectFit: "cover",
              borderRadius: 4,
              border: "1px solid #2a2a2a",
            }}
            alt="keyframe"
          />
        ) : (
          <div
            style={{
              width: 100,
              height: 70,
              background: "#1a1a1a",
              borderRadius: 4,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#333",
              fontSize: 9,
              letterSpacing: 1,
            }}
          >
            NO IMG
          </div>
        )}
        <div
          style={{
            fontSize: 9,
            color: "#333",
            marginTop: 4,
            fontFamily: "monospace",
            textAlign: "center",
          }}
        >
          #{e.id} · {e.camera_id || "—"}
        </div>
      </div>

      {/* Details */}
      <div>
        {/* Timestamps */}
        <div
          style={{
            display: "flex",
            gap: 16,
            marginBottom: 12,
            fontSize: 11,
            fontFamily: "monospace",
          }}
        >
          <div>
            <span style={{ color: "#444", marginRight: 6 }}>FROM</span>
            <span style={{ color: "#bbb" }}>{fmt(e.started_at)}</span>
          </div>
          <div>
            <span style={{ color: "#444", marginRight: 6 }}>TO</span>
            <span style={{ color: e.ended_at ? "#bbb" : "#555" }}>
              {fmt(e.ended_at) || "ongoing…"}
            </span>
          </div>
        </div>

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
            label="Duration"
            value={`${e.duration?.toFixed(1)}s`}
            accent={accent}
          />
          <Badge
            label="Inactive"
            value={`${e.inactive_seconds?.toFixed(1)}s`}
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
          <Badge label="Trigger" value={e.trigger || "—"} accent="#888" />
        </div>

        {/* Summary */}
        <div
          style={{
            fontSize: 12,
            color: "#666",
            lineHeight: 1.6,
            borderTop: "1px solid #1a1a1a",
            paddingTop: 8,
          }}
        >
          {e.summary || (
            <span style={{ color: "#333" }}>Generating summary…</span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Events() {
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = () =>
      getEvents()
        .then((r) => {
          setEvents(r.data);
          setError(null);
        })
        .catch((e) => setError(String(e)));
    load();
    const iv = setInterval(load, 4000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <h2
          style={{
            fontSize: 11,
            letterSpacing: 4,
            color: "#555",
            textTransform: "uppercase",
            margin: 0,
          }}
        >
          Sleep Records
        </h2>
        <span style={{ fontSize: 11, color: "#333", fontFamily: "monospace" }}>
          {events.length} event{events.length !== 1 ? "s" : ""}
        </span>
      </div>

      {error && <p style={{ color: "#ff4444", fontSize: 12 }}>⚠ {error}</p>}

      {events.length === 0 ? (
        <p style={{ color: "#2a2a2a", fontSize: 12, fontFamily: "monospace" }}>
          No events recorded yet.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {events.map((e) => (
            <EventCard key={e.id} e={e} />
          ))}
        </div>
      )}
    </div>
  );
}
