export type Lane = "North" | "South" | "East" | "West";
export type LightColor = "RED" | "YELLOW" | "GREEN";

export interface SignalUpdate {
  type: "SIGNAL_UPDATE" | "EMERGENCY_OVERRIDE" | "DENSITY_UPDATE";
  intersection: string;
  lights: Record<Lane, LightColor>;
  densities: Record<Lane, number>;
  active_emergency: boolean;
  ts: number;
  cycle_count: number;
  avg_wait_seconds: number;
  last_event: string;
}
