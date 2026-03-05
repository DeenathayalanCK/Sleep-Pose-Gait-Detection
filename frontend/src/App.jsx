import LiveStream from "./components/LiveStream";
import LiveStatus from "./components/LiveStatus";
import PersonList from "./components/Personlist";
import Events from "./components/Events";

export default function App() {
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
      {/* Top row: stream + live status */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 340px",
          gap: 24,
          marginBottom: 32,
        }}
      >
        <LiveStream />
        <LiveStatus />
      </div>

      {/* Middle row: person sessions table */}
      <div
        style={{
          background: "#0a0a0a",
          border: "1px solid #1a1a1a",
          borderRadius: 12,
          padding: "20px 24px",
          marginBottom: 32,
        }}
      >
        <PersonList />
      </div>

      {/* Bottom: sleep events */}
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
    </div>
  );
}
