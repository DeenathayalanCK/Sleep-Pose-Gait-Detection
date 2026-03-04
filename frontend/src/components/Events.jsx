import { useEffect, useState } from "react";
import { getEvents } from "../api";

export default function Events() {
  const [events, setEvents] = useState([]);

  const loadEvents = () => {
    getEvents().then((res) => {
      setEvents(res.data);
    });
  };

  useEffect(() => {
    loadEvents();

    const interval = setInterval(loadEvents, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h2>Fatigue Events</h2>

      <table border="1" cellPadding="10">
        <thead>
          <tr>
            <th>ID</th>
            <th>Timestamp</th>
            <th>Duration</th>
            <th>Snapshot</th>
            <th>Summary</th>
          </tr>
        </thead>

        <tbody>
          {events.map((e) => (
            <tr key={e.id}>
              <td>{e.id}</td>

              <td>{e.timestamp}</td>

              <td>{e.duration}</td>

              <td>
                <img src={`http://localhost:8000/${e.snapshot}`} width="120" />
              </td>

              <td>{e.summary}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
