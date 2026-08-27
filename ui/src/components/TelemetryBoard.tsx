import type { TelemetryPoint } from "../types";

export function TelemetryBoard({ points }: { points: TelemetryPoint[] }) {
  return (
    <section className="panel">
      <h2>Live Telemetry</h2>
      {points.length === 0 ? (
        <p className="muted">Waiting for data…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Device</th>
              <th>Power (kW)</th>
              <th>Voltage (V)</th>
            </tr>
          </thead>
          <tbody>
            {points
              .slice()
              .sort((a, b) => a.device_id.localeCompare(b.device_id))
              .map((p) => (
                <tr key={p.device_id}>
                  <td>{p.device_id}</td>
                  <td>{p.power_kw.toFixed(2)}</td>
                  <td>{p.voltage_v.toFixed(1)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
