import { useState } from "react";
import LiveStream from "./components/LiveStream";
import LiveStatus from "./components/LiveStatus";
import PersonList from "./components/PersonList";
import Events from "./components/Events";
import Calibration from "./components/Calibration";

const TABS = ["Live", "Records", "Persons", "Calibrate"];

export default function App() {
  const [tab, setTab] = useState("Live");

  return (
    <div
      style={{
        background: "#050505",
        minHeight: "100vh",
        color: "#eee",
        fontFamily: "'Courier New', monospace",
        padding: "24px 32px",
      }}
    >
      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 24,
          borderBottom: "1px solid #111",
          paddingBottom: 12,
        }}
      >
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              background: tab === t ? "#1a1a1a" : "transparent",
              border: `1px solid ${tab === t ? "#444" : "#1a1a1a"}`,
              borderRadius: 6,
              padding: "6px 18px",
              cursor: "pointer",
              color: tab === t ? "#eee" : "#444",
              fontSize: 11,
              fontFamily: "monospace",
              letterSpacing: 2,
            }}
          >
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      {tab === "Live" && (
        <div
          style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 24 }}
        >
          <LiveStream />
          <LiveStatus />
        </div>
      )}

      {tab === "Records" && (
        <div
          style={{
            background: "#0a0a0a",
            border: "1px solid #1a1a1a",
            borderRadius: 12,
            padding: "20px 24px",
          }}
        >
          <Events />
        </div>
      )}

      {tab === "Persons" && (
        <div
          style={{
            background: "#0a0a0a",
            border: "1px solid #1a1a1a",
            borderRadius: 12,
            padding: "20px 24px",
          }}
        >
          <PersonList />
        </div>
      )}

      {tab === "Calibrate" && (
        <div
          style={{
            background: "#0a0a0a",
            border: "1px solid #1a1a1a",
            borderRadius: 12,
            padding: "20px 24px",
          }}
        >
          <Calibration />
        </div>
      )}
    </div>
  );
}
