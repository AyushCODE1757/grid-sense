"use client";

import { useEffect, useMemo, useState } from "react";

import type { Lane, LightColor, SignalUpdate } from "@/types/traffic";

const LANES: Lane[] = ["North", "South", "East", "West"];
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

const defaultUpdate: SignalUpdate = {
  type: "SIGNAL_UPDATE",
  intersection: "INT-001",
  lights: { North: "GREEN", South: "RED", East: "RED", West: "RED" },
  densities: { North: 0, South: 0, East: 0, West: 0 },
  active_emergency: false,
  ts: Math.floor(Date.now() / 1000),
  cycle_count: 0,
  avg_wait_seconds: 0,
  last_event: "Booting",
};

function lampClass(color: LightColor) {
  if (color === "GREEN") return "bg-emerald-500 shadow-[0_0_30px_#2ecc71]";
  if (color === "YELLOW") return "bg-amber-400 shadow-[0_0_30px_#f9c74f]";
  return "bg-rose-500 shadow-[0_0_20px_#ff4d6d66]";
}

export default function Page() {
  const [state, setState] = useState<SignalUpdate>(defaultUpdate);
  const [eventLog, setEventLog] = useState<string[]>([]);
  const [streamStatus, setStreamStatus] = useState("Connecting...");
  const [reconnectMs, setReconnectMs] = useState(1000);

  useEffect(() => {
    let es: EventSource | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      setStreamStatus("Live");
      es = new EventSource(`${BACKEND_URL}/stream`);

      es.onmessage = (event) => {
        const parsed = JSON.parse(event.data) as SignalUpdate;
        setState(parsed);
        setEventLog((prev) => {
          const line = `${new Date(parsed.ts * 1000).toLocaleTimeString()} - ${parsed.last_event}`;
          return [line, ...prev].slice(0, 20);
        });
        setReconnectMs(1000);
      };

      es.onerror = () => {
        setStreamStatus("Reconnecting...");
        es?.close();
        timer = setTimeout(connect, reconnectMs);
        setReconnectMs((prev) => Math.min(prev * 2, 15000));
      };
    };

    connect();

    return () => {
      if (timer) clearTimeout(timer);
      es?.close();
    };
  }, [reconnectMs]);

  const totalVehicles = useMemo(
    () => LANES.reduce((acc, lane) => acc + Math.round((state.densities[lane] / 100) * 50), 0),
    [state.densities]
  );

  const triggerEmergency = async (lane: Lane) => {
    await fetch(`${BACKEND_URL}/emergency`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lane, duration_seconds: 30 }),
    });
  };

  return (
    <main className="mx-auto min-h-screen max-w-6xl p-6 md:p-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-[#1c2541cc] p-4">
        <h1 className="text-2xl font-semibold md:text-3xl">AI Traffic Command Center</h1>
        <div className="flex items-center gap-3 text-sm">
          <span className="rounded-full bg-sky-900 px-3 py-1">Intersection: {state.intersection}</span>
          <span className="rounded-full bg-slate-900 px-3 py-1">SSE: {streamStatus}</span>
        </div>
      </header>

      <section className="mb-6 grid gap-4 md:grid-cols-4">
        <div className="rounded-xl bg-[#1c2541cc] p-4">Total Vehicles: {totalVehicles}</div>
        <div className="rounded-xl bg-[#1c2541cc] p-4">Avg Wait: {state.avg_wait_seconds.toFixed(1)}s</div>
        <div className="rounded-xl bg-[#1c2541cc] p-4">Cycle Count: {state.cycle_count}</div>
        <div className="rounded-xl bg-[#1c2541cc] p-4">Emergency: {state.active_emergency ? "ACTIVE" : "OFF"}</div>
      </section>

      <section className="mb-6 grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl bg-[#1c2541cc] p-6">
          <h2 className="mb-5 text-xl font-medium">Intersection Grid</h2>
          <div className="grid grid-cols-2 gap-6">
            {LANES.map((lane) => (
              <div key={lane} className="rounded-xl border border-slate-700 p-4 text-center">
                <p className="mb-3 text-lg">{lane}</p>
                <div className={`mx-auto h-24 w-24 rounded-full transition-all duration-700 ${lampClass(state.lights[lane])}`} />
                <p className="mt-2 text-sm text-slate-300">{state.lights[lane]}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl bg-[#1c2541cc] p-6">
          <h2 className="mb-5 text-xl font-medium">Lane Density</h2>
          <div className="space-y-4">
            {LANES.map((lane) => (
              <div key={lane}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{lane}</span>
                  <span>{state.densities[lane].toFixed(1)}%</span>
                </div>
                <div className="h-4 w-full rounded-full bg-slate-700">
                  <div
                    className="h-4 rounded-full bg-cyan-400 transition-all duration-700"
                    style={{ width: `${state.densities[lane]}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <h3 className="mt-8 mb-3 text-lg">Emergency Override</h3>
          <div className="grid grid-cols-2 gap-3">
            {LANES.map((lane) => (
              <button
                key={lane}
                onClick={() => triggerEmergency(lane)}
                className="rounded-xl bg-rose-600 p-3 font-semibold hover:bg-rose-500"
              >
                Simulate Ambulance {lane}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-2xl bg-[#1c2541cc] p-6">
        <h2 className="mb-4 text-xl font-medium">Event Log (last 20)</h2>
        <div className="max-h-56 space-y-2 overflow-auto rounded-xl bg-[#0b132b] p-4 text-sm text-slate-200">
          {eventLog.length === 0 && <p>No events yet...</p>}
          {eventLog.map((line, idx) => (
            <p key={`${line}-${idx}`}>{line}</p>
          ))}
        </div>
      </section>
    </main>
  );
}
