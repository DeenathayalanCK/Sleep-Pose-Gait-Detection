import Health from "./components/Health";
import Events from "./components/Events";

function App() {
  return (
    <div style={{ padding: 40, fontFamily: "Arial" }}>
      <h1>Fatigue Monitoring Dashboard</h1>

      <Health />

      <Events />
    </div>
  );
}

export default App;
