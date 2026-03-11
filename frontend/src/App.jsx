import { useState } from "react";
import LiveStream from "./components/LiveStream";
import LiveStatus from "./components/LiveStatus";
import PersonList from "./components/PersonList";
import Events from "./components/Events";
import Calibration from "./components/Calibration";
import Evaluate from "./components/Evaluate";

const TABS = ["Live", "Records", "Persons", "Calibrate", "Evaluate"];

const TAB_ACCENT = {
  Evaluate: "#00bcd4",
};

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
        {TABS.map((t) => {
          const accent = TAB_ACCENT[t];
          const active = tab === t;
          return (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                background: active
                  ? accent
                    ? accent + "18"
                    : "#1a1a1a"
                  : "transparent",
                border: `1px solid ${active ? accent || "#444" : "#1a1a1a"}`,
                borderRadius: 6,
                padding: "6px 18px",
                cursor: "pointer",
                color: active ? accent || "#eee" : "#444",
                fontSize: 11,
                fontFamily: "monospace",
                letterSpacing: 2,
              }}
            >
              {t.toUpperCase()}
            </button>
          );
        })}
      </div>

      {tab === "Live" && (
        <div
          style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 24 }}
        >
          <LiveStream />
          <LiveStatus />
        </div>
      )}

      {["Records", "Persons", "Calibrate", "Evaluate"].includes(tab) && (
        <div
          style={{
            background: "#0a0a0a",
            border: "1px solid #1a1a1a",
            borderRadius: 12,
            padding: "20px 24px",
          }}
        >
          {tab === "Records" && <Events />}
          {tab === "Persons" && <PersonList />}
          {tab === "Calibrate" && <Calibration />}
          {tab === "Evaluate" && <Evaluate />}
        </div>
      )}
    </div>
  );
}
