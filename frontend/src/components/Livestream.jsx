import { useState, useEffect, useRef, useCallback } from "react";

const STREAM_URL = "http://localhost:8000/stream";
const STATUS_URL = "http://localhost:8000/status";

/*
  ROOT CAUSE OF CONSTANT DISCONNECTS — was in the old code:

  1. onLoad fires ONCE when the HTTP connection opens, never again per frame.
     The watchdog setTimeout fired every 4s and called setStatus("offline")
     even while the stream was perfectly healthy, because resetWatchdog()
     was never called after the initial connect.

  2. setStatus("offline") triggered the retry useEffect which set a new img.src,
     tearing down the MJPEG connection and forcing a full reconnect — which
     triggers onLoad once → watchdog starts again → kills it in 4s → repeat.

  3. Setting img.src to a new value (with ?t=...) also causes a React re-render
     which could unmount/remount the <img>, further breaking the connection.

  THE FIX:
  - Remove the watchdog timer entirely. MJPEG streams don't fire onLoad per frame.
  - Instead: poll /status every 2s. If we get a valid response with persons
    OR a counter > 0 from the stream, the backend is alive → show as LIVE.
  - Use a single stable img.src — never change it unless actually reconnecting
    after a confirmed backend outage (HTTP error, not just silence).
  - onError is the only reliable signal that the stream is truly broken.
*/

export default function LiveStream() {
  const [status, setStatus] = useState("connecting");
  const [procFps, setProcFps] = useState(null);
  const [personCnt, setPersonCnt] = useState(null);
  const imgRef = useRef(null);
  const retryTimer = useRef(null);
  const backendOk = useRef(false); // tracks if backend is reachable

  // ── Poll /status to confirm backend is alive and get person count ──
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(STATUS_URL, { cache: "no-store" });
        const d = await r.json();
        backendOk.current = true;

        const persons = Object.values(d || {});
        setPersonCnt(persons.length);

        // If we were waiting/offline but backend responds → stream should be live
        setStatus((prev) => (prev !== "live" ? "live" : "live"));
      } catch (_) {
        backendOk.current = false;
        // Backend unreachable — only then mark offline
        setStatus("offline");
      }
    };

    poll(); // immediate first check
    const iv = setInterval(poll, 2000);
    return () => clearInterval(iv);
  }, []);

  // ── onError — only real signal that the stream HTTP connection broke ──
  const handleError = useCallback(() => {
    setStatus("offline");
    // Schedule a reconnect attempt — replace src to force browser to retry
    if (retryTimer.current) clearTimeout(retryTimer.current);
    retryTimer.current = setTimeout(() => {
      if (imgRef.current) {
        // Add cache-buster to force a fresh HTTP request
        imgRef.current.src = `${STREAM_URL}?t=${Date.now()}`;
      }
    }, 3000);
  }, []);

  // ── onLoad — HTTP connection established (fires once per connect) ──
  const handleLoad = useCallback(() => {
    // Stream connection is open — mark live if backend also confirmed healthy
    setStatus("live");
  }, []);

  // Cleanup retry timer on unmount
  useEffect(
    () => () => {
      if (retryTimer.current) clearTimeout(retryTimer.current);
    },
    [],
  );

  const isLive = status === "live";
  const dotColor = isLive
    ? "#ff3030"
    : status === "connecting"
      ? "#ff8c00"
      : "#555";

  return (
    <div
      style={{
        background: "#0d0d0d",
        border: "1px solid #1e1e1e",
        borderRadius: 12,
        overflow: "hidden",
      }}
    >
      {/* ── Header bar ─────────────────────────────────────────── */}
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
        {/* Live dot */}
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: dotColor,
            boxShadow: isLive ? `0 0 8px ${dotColor}` : "none",
            animation: isLive ? "livepulse 1.4s ease-in-out infinite" : "none",
          }}
        />

        <span
          style={{
            fontSize: 11,
            letterSpacing: 3,
            fontFamily: "monospace",
            color: dotColor,
            textTransform: "uppercase",
          }}
        >
          {isLive
            ? "LIVE"
            : status === "connecting"
              ? "CONNECTING…"
              : "STREAM OFFLINE"}
        </span>

        {/* Right side — person count + resolution */}
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            gap: 14,
            alignItems: "center",
          }}
        >
          {personCnt !== null && isLive && (
            <span
              style={{
                fontSize: 10,
                color: "#00bcd4",
                fontFamily: "monospace",
              }}
            >
              {personCnt} person{personCnt !== 1 ? "s" : ""}
            </span>
          )}
          {procFps !== null && (
            <span
              style={{ fontSize: 10, color: "#555", fontFamily: "monospace" }}
            >
              {procFps.toFixed(1)} fps
            </span>
          )}
          <span
            style={{ fontSize: 10, color: "#333", fontFamily: "monospace" }}
          >
            CCTV · 640×480
          </span>
        </div>
      </div>

      {/* ── Video area ─────────────────────────────────────────── */}
      <div style={{ position: "relative", background: "#000", lineHeight: 0 }}>
        {/*
          img is ALWAYS mounted — never conditionally removed.
          Unmounting it tears down the HTTP connection.
          We hide it with CSS when offline, not with conditional rendering.
        */}
        <img
          ref={imgRef}
          src={STREAM_URL}
          alt="Live feed"
          onLoad={handleLoad}
          onError={handleError}
          style={{
            width: "100%",
            display: "block",
            maxHeight: 480,
            objectFit: "contain",
            // Fade out visually when not live, but keep the element mounted
            opacity: isLive ? 1 : 0,
            transition: "opacity 0.4s",
          }}
        />

        {/* Placeholder shown while connecting or offline */}
        {!isLive && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              minHeight: 260,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 14,
            }}
          >
            <div style={{ fontSize: 36 }}>📷</div>
            <div
              style={{
                color: "#2a2a2a",
                fontSize: 11,
                letterSpacing: 3,
                fontFamily: "monospace",
                textTransform: "uppercase",
              }}
            >
              {status === "connecting"
                ? "Connecting to stream…"
                : "Reconnecting…"}
            </div>
            <div
              style={{
                fontSize: 10,
                color: "#1a1a1a",
                fontFamily: "monospace",
              }}
            >
              {backendOk.current
                ? "Backend online — waiting for video frames"
                : "Waiting for backend at :8000"}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes livepulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.15; }
        }
      `}</style>
    </div>
  );
}
