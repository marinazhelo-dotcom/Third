export type Role = "admin" | "operator" | "viewer";

export interface Session {
  accessToken: string;
  username: string;
  role: Role;
}

export interface TelemetryPoint {
  device_id: string;
  timestamp: string;
  power_kw: number;
  voltage_v: number;
}

export interface AlertItem {
  id: number;
  device_id: string;
  message: string;
  power_kw: number;
  threshold: number;
  created_at: string;
  acknowledged: boolean;
  acknowledged_by: string | null;
}

export interface Rule {
  id: number;
  device_id: string;
  threshold: number;
  enabled: boolean;
}

export interface WsMessage {
  channel: string;
  data: unknown;
}
