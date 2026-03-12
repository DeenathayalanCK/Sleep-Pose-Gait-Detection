import { useEffect, useState } from "react";
import { getHealth } from "../api";
import axios from "axios";

const API = axios.create({ baseURL: "http://localhost:8000" });

export default function Health() {
  const [health, setHealth] = useState(null);
  const [resetting, setResetting] = useState(false);
  const [resetMsg, setResetMsg] = useState(null);

  useEffect(() => {
    getHealth().then((res) => setHealth(res.data));
  }, []);

  const handleReset = async () => {
    if (
      !window.confirm(
        "Reset all tracked identities?\n\n" +
          "This clears the ReID gallery and all person tracking history in memory.\n" +
          "Database events are NOT deleted.\n\n" +
          "Use this when deploying on a new group of people.",
      )
    )
      return;

    setResetting(true);
    setResetMsg(null);
    try {
      const res = await API.post("/reset-identities");
      setResetMsg({ ok: true, text: res.data.message });
    } catch (e) {
      setResetMsg({
        ok: false,
        text: "Reset failed: " + (e.message || "unknown error"),
      });
    } finally {
      setResetting(false);
    }
  };

  if (!health)
    return <p style={{ color: "#666", fontFamily: "monospace" }}>Loading...</p>;

  return (
    <div style={{ fontFamily: "monospace" }}>
      <div
        style={{
          background: "#0a0a0a",
          border: "1px solid #1a1a1a",
          borderRadius: 8,
          padding: "16px 20px",
          marginBottom: 16,
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: "#444",
            letterSpacing: 2,
            marginBottom: 10,
          }}
        >
          SYSTEM HEALTH
        </div>
        <div style={{ display: "flex", gap: 24 }}>
          <span>
            Status:{" "}
            <span
              style={{
                color: health.status === "running" ? "#4caf50" : "#ff5252",
              }}
            >
              {health.status}
            </span>
          </span>
          <span style={{ color: "#555" }}>{health.service}</span>
        </div>
      </div>

      {/* ── Reset Identities ── */}
      <div
        style={{
          background: "#0a0a0a",
          border: "1px solid #2a1a1a",
          borderRadius: 8,
          padding: "16px 20px",
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: "#664",
            letterSpacing: 2,
            marginBottom: 8,
          }}
        >
          IDENTITY MANAGEMENT
        </div>
        <p style={{ color: "#888", fontSize: 12, margin: "0 0 12px" }}>
          Clear all tracked persons and ReID gallery. Use before deploying on a
          new group of people so old identity embeddings don't cause mismatches.
          Database events are preserved.
        </p>
        <button
          onClick={handleReset}
          disabled={resetting}
          style={{
            background: resetting ? "#1a1a1a" : "#1a0a0a",
            border: "1px solid #ff4444",
            borderRadius: 6,
            padding: "8px 20px",
            color: resetting ? "#555" : "#ff6666",
            cursor: resetting ? "not-allowed" : "pointer",
            fontSize: 11,
            letterSpacing: 2,
            fontFamily: "monospace",
          }}
        >
          {resetting ? "RESETTING..." : "⟳  RESET IDENTITIES"}
        </button>

        {resetMsg && (
          <div
            style={{
              marginTop: 10,
              padding: "8px 12px",
              background: resetMsg.ok ? "#0a1a0a" : "#1a0a0a",
              border: `1px solid ${resetMsg.ok ? "#4caf50" : "#ff4444"}`,
              borderRadius: 6,
              color: resetMsg.ok ? "#4caf50" : "#ff6666",
              fontSize: 12,
            }}
          >
            {resetMsg.text}
          </div>
        )}
      </div>
    </div>
  );
}
