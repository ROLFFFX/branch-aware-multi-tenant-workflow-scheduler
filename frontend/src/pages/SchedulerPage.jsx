import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";

export function SchedulerPage() {
  const [state, setState] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  async function loadState() {
    try {
      setLoading(true);
      setErr(null);
      const s = await api.getSchedulerState();
      setState(s);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadState();
    const id = setInterval(loadState, 5000);
    return () => clearInterval(id);
  }, []);

  async function run() {
    try {
      await api.startScheduler();
      loadState();
    } catch (e) {
      setErr(e.message);
    }
  }

  async function pause() {
    try {
      await api.pauseScheduler();
      loadState();
    } catch (e) {
      setErr(e.message);
    }
  }

  const rawState = typeof state === "string" ? state : JSON.stringify(state);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Scheduler</h2>
          <p className="text-xs text-gray-500">
            Global control for worker loops, user concurrency, and queue
            execution.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={run}
            className="px-4 py-2 rounded-md bg-emerald-600 hover:bg-emerald-500 text-sm font-medium text-white"
          >
            Run
          </button>
          <button
            onClick={pause}
            className="px-4 py-2 rounded-md bg-red-600 hover:bg-red-500 text-sm font-medium text-white"
          >
            Pause
          </button>
        </div>
      </div>

      {err && (
        <div className="text-xs text-red-400 bg-red-900/30 border border-red-700 rounded-md px-3 py-2">
          {err}
        </div>
      )}

      <div className="bg-white/60 border bg-gray-200 rounded-lg p-4 text-xs">
        <div className="flex items-center justify-between mb-2">
          <span className="text-slate-300">Scheduler state</span>
          {loading && (
            <span className="text-[10px] text-gray-9000">Refreshing...</span>
          )}
        </div>
        <pre className="bg-white border bg-gray-200 rounded-md p-2 font-mono text-[11px] overflow-auto">
          {rawState ?? "No state yet."}
        </pre>
      </div>
    </div>
  );
}
