import type { AlertItem } from "../types";

interface Props {
  alerts: AlertItem[];
  canAck: boolean;
  onAck: (id: number) => Promise<void>;
}

export function AlertsFeed({ alerts, canAck, onAck }: Props) {
  return (
    <section className="panel">
      <h2>Alerts</h2>
      {alerts.length === 0 ? (
        <p className="muted">No alerts yet.</p>
      ) : (
        <ul className="alerts">
          {alerts.map((a) => (
            <li key={a.id} className={a.acknowledged ? "ack" : ""}>
              <div className="alert-row">
                <strong>{a.device_id}</strong>
                <span className="muted">{new Date(a.created_at).toLocaleTimeString()}</span>
              </div>
              <div>{a.message}</div>
              <div className="alert-actions">
                {a.acknowledged ? (
                  <span className="muted">acked by {a.acknowledged_by}</span>
                ) : canAck ? (
                  <button onClick={() => onAck(a.id)}>Acknowledge</button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
