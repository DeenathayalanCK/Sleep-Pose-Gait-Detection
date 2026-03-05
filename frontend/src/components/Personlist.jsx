import { useEffect, useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

function fmt(iso) {
  return iso ? iso.replace("T", " ").slice(0, 19) : "—";
}

function dur(secs) {
  if (!secs) return "0s";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

const STATE_ICON = {
  sleeping: "😴",
  drowsy: "😪",
  inactive: "💤",
  sitting: "🪑",
  standing: "🧍",
  walking: "🚶",
  awake: "👁️",
  unknown: "—",
};

export default function PersonList() {
  const [persons, setPersons] = useState([]);

  useEffect(() => {
    const load = () =>
      axios
        .get(`${API}/persons`)
        .then((r) => setPersons(r.data))
        .catch(() => {});
    load();
    const iv = setInterval(load, 3000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div>
      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          marginBottom: 14,
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
          Person Sessions
        </h2>
        <span style={{ fontSize: 11, color: "#333", fontFamily: "monospace" }}>
          {persons.length} tracked
        </span>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 11,
            fontFamily: "monospace",
          }}
        >
          <thead>
            <tr style={{ borderBottom: "1px solid #1a1a1a" }}>
              {[
                "ID",
                "First Seen",
                "Last Seen",
                "Total Time",
                "Last State",
              ].map((h) => (
                <th
                  key={h}
                  style={{
                    padding: "6px 10px",
                    color: "#444",
                    letterSpacing: 2,
                    textAlign: "left",
                    fontWeight: 400,
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {persons.map((p) => (
              <tr
                key={p.id}
                style={{
                  borderBottom: "1px solid #111",
                  background:
                    p.last_state === "sleeping" ? "#110000" : "transparent",
                }}
              >
                <td
                  style={{
                    padding: "7px 10px",
                    color: "#00bcd4",
                    fontWeight: 700,
                  }}
                >
                  P{p.track_id}
                </td>
                <td style={{ padding: "7px 10px", color: "#555" }}>
                  {fmt(p.first_seen)}
                </td>
                <td style={{ padding: "7px 10px", color: "#777" }}>
                  {fmt(p.last_seen)}
                </td>
                <td style={{ padding: "7px 10px", color: "#aaa" }}>
                  {dur(p.total_duration)}
                </td>
                <td style={{ padding: "7px 10px" }}>
                  <span
                    style={{
                      color:
                        p.last_state === "sleeping"
                          ? "#ff2020"
                          : p.last_state === "drowsy"
                            ? "#ff8c00"
                            : "#555",
                    }}
                  >
                    {STATE_ICON[p.last_state] || ""} {p.last_state || "—"}
                  </span>
                </td>
              </tr>
            ))}
            {persons.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  style={{
                    padding: "12px 10px",
                    color: "#222",
                    textAlign: "center",
                  }}
                >
                  No sessions recorded yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
