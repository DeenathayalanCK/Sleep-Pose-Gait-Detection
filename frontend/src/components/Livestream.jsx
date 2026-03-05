import { useState } from "react";

export default function LiveStream() {
  const [error, setError] = useState(false);

  return (
    <div
      style={{
        background: "#0d0d0d",
        border: "1px solid #1e1e1e",
        borderRadius: 12,
        overflow: "hidden",
        marginBottom: 28,
        position: "relative",
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 16px",
          borderBottom: "1px solid #1a1a1a",
          background: "#111",
        }}
      >
        {/* Pulsing live dot */}
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: error ? "#555" : "#ff3030",
            boxShadow: error ? "none" : "0 0 8px #ff3030",
            animation: error ? "none" : "livepulse 1.4s ease-in-out infinite",
          }}
        />
        <span
          style={{
            fontSize: 11,
            letterSpacing: 3,
            color: error ? "#444" : "#ff5555",
            textTransform: "uppercase",
            fontFamily: "monospace",
          }}
        >
          {error ? "Stream Offline" : "Live"}
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 10,
            color: "#333",
            fontFamily: "monospace",
          }}
        >
          CCTV · 640×480
        </span>
      </div>

      {/* Video */}
      <div style={{ position: "relative", background: "#000", lineHeight: 0 }}>
        {!error ? (
          <img
            src="http://localhost:8000/stream"
            alt="Live feed"
            onError={() => setError(true)}
            style={{
              width: "100%",
              display: "block",
              maxHeight: 480,
              objectFit: "contain",
            }}
          />
        ) : (
          <div
            style={{
              height: 320,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
            }}
          >
            <div style={{ fontSize: 32 }}>📷</div>
            <div
              style={{
                color: "#333",
                fontSize: 12,
                letterSpacing: 2,
                fontFamily: "monospace",
                textTransform: "uppercase",
              }}
            >
              Waiting for stream…
            </div>
            <button
              onClick={() => setError(false)}
              style={{
                marginTop: 8,
                padding: "6px 18px",
                background: "transparent",
                border: "1px solid #333",
                color: "#555",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 11,
                letterSpacing: 2,
                fontFamily: "monospace",
              }}
            >
              RETRY
            </button>
          </div>
        )}
      </div>

      <style>{`
        @keyframes livepulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.2; }
        }
      `}</style>
    </div>
  );
}
