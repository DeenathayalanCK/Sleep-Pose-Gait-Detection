import { useEffect, useState } from "react";
import { getHealth } from "../api";

export default function Health() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth().then((res) => {
      setHealth(res.data);
    });
  }, []);

  if (!health) return <p>Loading...</p>;

  return (
    <div style={{ marginBottom: 20 }}>
      <h2>System Health</h2>
      <p>Status: {health.status}</p>
      <p>Service: {health.service}</p>
    </div>
  );
}
