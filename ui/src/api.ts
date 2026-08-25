import type { AlertItem, Rule, Session } from "./types";

const BASE = "/api";

function headers(token?: string): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

export async function login(username: string, password: string): Promise<Session> {
  const resp = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) throw new Error("Login failed");
  const data = await resp.json();
  return { accessToken: data.access_token, username: data.username, role: data.role };
}

export async function fetchRules(token: string): Promise<Rule[]> {
  const resp = await fetch(`${BASE}/rules`, { headers: headers(token) });
  if (!resp.ok) throw new Error("Failed to load rules");
  return resp.json();
}

export async function createRule(
  token: string,
  device_id: string,
  threshold: number,
): Promise<Rule> {
  const resp = await fetch(`${BASE}/rules`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify({ device_id, threshold }),
  });
  if (!resp.ok) throw new Error("Failed to create rule");
  return resp.json();
}

export async function deleteRule(token: string, id: number): Promise<void> {
  const resp = await fetch(`${BASE}/rules/${id}`, { method: "DELETE", headers: headers(token) });
  if (!resp.ok) throw new Error("Failed to delete rule");
}

export async function fetchAlerts(token: string): Promise<AlertItem[]> {
  const resp = await fetch(`${BASE}/alerts`, { headers: headers(token) });
  if (!resp.ok) throw new Error("Failed to load alerts");
  return resp.json();
}

export async function ackAlert(token: string, id: number): Promise<void> {
  const resp = await fetch(`${BASE}/alerts/${id}/ack`, {
    method: "POST",
    headers: headers(token),
  });
  if (!resp.ok) throw new Error("Failed to acknowledge alert");
}
