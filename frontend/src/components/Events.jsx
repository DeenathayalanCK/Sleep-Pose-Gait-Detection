import { useEffect, useState } from "react";
import { getEvents } from "../api";

function snapshotUrl(path) {
  if (!path) return null;
  return `http://localhost:8000/snapshots/${path.split("/").pop()}`;
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
    const iv = setInterval(load, 5000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div>
      <h2
        style={{
          color: "#888",
          fontSize: 12,
          letterSpacing: 4,
          textTransform: "uppercase",
          marginBottom: 16,
        }}
      >
        Sleep Events
      </h2>

      {error && <p style={{ color: "#ff4444", fontSize: 12 }}>⚠ {error}</p>}

      {events.length === 0 ? (
        <p style={{ color: "#444", fontSize: 13 }}>No events yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {events.map((e) => (
            <div
              key={e.id}
              style={{
                background: "#0d0d0d",
                border: "1px solid #222",
                borderRadius: 8,
                padding: "16px 20px",
                display: "grid",
                gridTemplateColumns: "auto 1fr auto",
                gap: 16,
                alignItems: "start",
              }}
            >
              <div style={{ textAlign: "center" }}>
                {snapshotUrl(e.snapshot) ? (
                  <img
                    src={snapshotUrl(e.snapshot)}
                    width={80}
                    style={{ borderRadius: 4, border: "1px solid #333" }}
                    alt=""
                  />
                ) : (
                  <div
                    style={{
                      width: 80,
                      height: 56,
                      background: "#1a1a1a",
                      borderRadius: 4,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#333",
                      fontSize: 10,
                    }}
                  >
                    NO IMG
                  </div>
                )}
              </div>
              <div>
                <div
                  style={{
                    color: "#ff2020",
                    fontSize: 11,
                    letterSpacing: 3,
                    textTransform: "uppercase",
                    marginBottom: 4,
                  }}
                >
                  SLEEP DETECTED
                </div>
                <div style={{ color: "#666", fontSize: 11, marginBottom: 6 }}>
                  {e.timestamp} &nbsp;·&nbsp; {e.duration?.toFixed(1)}s
                </div>
                <div style={{ color: "#999", fontSize: 12, lineHeight: 1.6 }}>
                  {e.summary || "—"}
                </div>
              </div>
              <div
                style={{ color: "#333", fontSize: 11, fontFamily: "monospace" }}
              >
                #{e.id}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
