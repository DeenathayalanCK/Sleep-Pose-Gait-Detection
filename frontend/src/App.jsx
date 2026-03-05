import LiveStatus from "./components/Livestatus";
import LiveStream from "./components/Livestream";
import Events from "./components/Events";

export default function App() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a0a0a",
        color: "#ccc",
        fontFamily: "'Courier New', monospace",
        padding: "36px 48px",
        maxWidth: 960,
        margin: "0 auto",
      }}
    >
      {/* Title */}
      <div style={{ marginBottom: 32 }}>
        <div
          style={{
            fontSize: 10,
            letterSpacing: 6,
            color: "#333",
            textTransform: "uppercase",
            marginBottom: 6,
          }}
        >
          Sleep Detection System
        </div>
        <h1
          style={{
            fontSize: 26,
            fontWeight: 700,
            color: "#fff",
            letterSpacing: 2,
            margin: 0,
          }}
        >
          CCTV Monitor
        </h1>
      </div>

      {/* Two-column: stream left, status right */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 320px",
          gap: 24,
          marginBottom: 32,
          alignItems: "start",
        }}
      >
        <LiveStream />
        <LiveStatus />
      </div>

      <Events />
    </div>
  );
}
