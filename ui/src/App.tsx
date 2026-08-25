import { useCallback, useEffect, useState } from "react";
import { ackAlert, fetchAlerts, fetchRules } from "./api";
import { AlertsFeed } from "./components/AlertsFeed";
import { Login } from "./components/Login";
import { RulesPanel } from "./components/RulesPanel";
import { TelemetryBoard } from "./components/TelemetryBoard";
import type { AlertItem, Rule, Session, TelemetryPoint, WsMessage } from "./types";

const SESSION_KEY = "third_session";

function loadSession(): Session | null {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export default function App() {
  const [session, setSession] = useState<Session | null>(loadSession);
  const [telemetry, setTelemetry] = useState<Record<string, TelemetryPoint>>({});
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [wsStatus, setWsStatus] = useState<string>("disconnected");

  const isAdmin = session?.role === "admin";
  const canAck = session?.role === "admin" || session?.role === "operator";

  const refresh = useCallback(async (token: string) => {
    setAlerts(await fetchAlerts(token));
    setRules(await fetchRules(token));
  }, []);

  useEffect(() => {
    if (!session) return;
    refresh(session.accessToken).catch(() => {});
  }, [session, refresh]);

  useEffect(() => {
    if (!session) return;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws?token=${session.accessToken}`);

    ws.onopen = () => setWsStatus("connected");
    ws.onclose = () => setWsStatus("disconnected");
    ws.onerror = () => setWsStatus("error");
    ws.onmessage = (event) => {
      const msg: WsMessage = JSON.parse(event.data);
      if (msg.channel === "telemetry.live") {
        const point = msg.data as TelemetryPoint;
        setTelemetry((prev) => ({ ...prev, [point.device_id]: point }));
      } else if (msg.channel === "alerts") {
        const raw = msg.data as {
          alert_id: number;
          device_id: string;
          message: string;
          power_kw: number;
          threshold: number;
          produced_at: string;
        };
        const item: AlertItem = {
          id: raw.alert_id,
          device_id: raw.device_id,
          message: raw.message,
          power_kw: raw.power_kw,
          threshold: raw.threshold,
          created_at: raw.produced_at,
          acknowledged: false,
          acknowledged_by: null,
        };
        setAlerts((prev) => [item, ...prev].slice(0, 200));
      }
    };

    return () => ws.close();
  }, [session]);

  const handleLogin = (s: Session) => {
    localStorage.setItem(SESSION_KEY, JSON.stringify(s));
    setSession(s);
  };

  const handleLogout = () => {
    localStorage.removeItem(SESSION_KEY);
    setSession(null);
    setTelemetry({});
    setAlerts([]);
    setRules([]);
  };

  if (!session) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Third — Energy Platform</h1>
        <div className="app-header-right">
          <span className="badge">{session.role}</span>
          <span>{session.username}</span>
          <span className={`ws-dot ws-${wsStatus}`} title={`ws: ${wsStatus}`} />
          <button onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <main className="grid">
        <TelemetryBoard points={Object.values(telemetry)} />
        <AlertsFeed
          alerts={alerts}
          canAck={canAck}
          onAck={async (id) => {
            await ackAlert(session.accessToken, id);
            setAlerts((prev) =>
              prev.map((a) =>
                a.id === id
                  ? { ...a, acknowledged: true, acknowledged_by: session.username }
                  : a,
              ),
            );
          }}
        />
        <RulesPanel
          rules={rules}
          isAdmin={isAdmin}
          token={session.accessToken}
          onRuleChange={async () => setRules(await fetchRules(session.accessToken))}
        />
      </main>
    </div>
  );
}
