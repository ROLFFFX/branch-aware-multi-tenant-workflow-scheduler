// ======================================================
// SchedulerPage.jsx — Original Layout + Working Play/Pause
// ======================================================
import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";

// ---------------------- Circular Gauge ----------------------
function CircularGauge({ current, max, label }) {
  const percent = Math.min(1, current / max);
  const size = 70;
  const stroke = 6;

  const radius = (size - stroke) / 2;
  const circ = 2 * Math.PI * radius;
  const offset = circ * (1 - percent);

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#E5E7EB"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#10B981"
          strokeWidth={stroke}
          fill="none"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-300"
        />
      </svg>

      <div className="text-xs text-gray-700 mt-1">
        <span className="font-medium">{current}</span> / {max}
      </div>
      <div className="text-[10px] text-gray-500">{label}</div>
    </div>
  );
}

// ---------------------- Status Pill ----------------------
function StatusPill({ status }) {
  const color =
    status === "RUNNING"
      ? "bg-emerald-100 text-emerald-700"
      : status === "FAILED"
      ? "bg-red-100 text-red-700"
      : status === "SUCCESS"
      ? "bg-blue-100 text-blue-700"
      : "bg-gray-200 text-gray-700";

  return (
    <span className={`px-2 py-[2px] rounded text-[11px] font-medium ${color}`}>
      {status}
    </span>
  );
}

// ---------------------- Linear Progress Bar ----------------------
function ProgressBar({ percent }) {
  return (
    <div className="w-full bg-gray-200 rounded h-2 overflow-hidden">
      <div
        className="bg-emerald-500 h-2 transition-all"
        style={{ width: `${Math.min(100, percent * 100)}%` }}
      />
    </div>
  );
}

// Normalize backend {state: "..."} or "paused"
function normalizeState(raw) {
  if (!raw) return { state: "unknown" };
  if (typeof raw === "string") {
    return { state: raw.replace(/"/g, "").trim() };
  }
  if (raw.state) return raw;
  return { state: "unknown" };
}

function classify(global) {
  const progress = global.progress || {};

  const success = [];
  const failed = [];

  for (const job of Object.values(progress)) {
    if (job.status === "SUCCESS") success.push(job);
    else if (job.status === "FAILED") failed.push(job);
  }

  const running = (global.running_jobs || []).map((id) => ({
    job_id: id,
    status: "RUNNING",
    user_id: "(unknown)",
    percent: 0,
    updated_at: null,
  }));

  const pending = jobs.filter((j) => j.status === "PENDING");

  return { pending, running, success, failed };
}

export function SchedulerPage() {
  const [scheduler, setScheduler] = useState({ state: "unknown" });
  const [global, setGlobal] = useState(null);
  const [err, setErr] = useState(null);
  const [activeTab, setActiveTab] = useState("running");

  const MAX_USERS = 3;
  const MAX_RUNNING = 10;

  // ---------------------- Data Fetch ----------------------
  async function loadSchedulerState() {
    try {
      const raw = await api.getSchedulerState();
      setScheduler(normalizeState(raw));
    } catch (e) {
      setErr(e.message);
    }
  }

  async function loadGlobalStatus() {
    try {
      setGlobal(await api.getGlobalStatus());
    } catch {}
  }

  useEffect(() => {
    loadSchedulerState();
    loadGlobalStatus();
    const id = setInterval(() => {
      loadSchedulerState();
      loadGlobalStatus();
    }, 1500);

    return () => clearInterval(id);
  }, []);

  const isRunning = scheduler.state === "running";

  // ---------------------- RUN / PAUSE BUTTON ----------------------
  async function handleToggle() {
    try {
      if (isRunning) {
        await api.pauseScheduler();
      } else {
        await api.startScheduler();
      }
      await loadSchedulerState();
    } catch (e) {
      setErr(e.message);
    }
  }

  if (!global)
    return <div className="p-6 text-gray-600">Loading scheduler…</div>;

  // Global progress contains only started or finished jobs
  const progressJobs = Object.values(global.progress || {});

  // 🔥 Pending jobs come from Redis list
  const pending = (global.pending_jobs || []).map((job_id) => ({
    job_id,
    user_id: "(pending)",
    status: "PENDING",
    percent: 0,
    updated_at: null,
  }));

  // 🔥 Running jobs come from Redis set + maybe progress info
  const running = (global.running_jobs || []).map((job_id) => {
    const info = global.progress?.[job_id];
    return info
      ? info
      : {
          job_id,
          user_id: "(running)",
          status: "RUNNING",
          percent: 0,
          updated_at: null,
        };
  });

  // Success and failed always come from progress hash
  const success = progressJobs.filter((j) => j.status === "SUCCESS");
  const failed = progressJobs.filter((j) => j.status === "FAILED");

  const tabs = [
    { key: "pending", label: `Pending (${pending.length})` },
    { key: "running", label: `Running (${running.length})` },
    { key: "success", label: `Success (${success.length})` },
    { key: "failed", label: `Failed (${failed.length})` },
  ];

  const tabJobs =
    activeTab === "pending"
      ? pending
      : activeTab === "running"
      ? running
      : activeTab === "success"
      ? success
      : failed;
  console.log(global.active_users);
  // ---------------------- Render ----------------------
  return (
    <div className="space-y-6 p-4">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Scheduler</h2>
          <p className="text-xs text-gray-500">Real-time global execution</p>
        </div>

        {/* Play / Pause Toggle */}
        <button
          onClick={handleToggle}
          className={`px-4 py-2 rounded text-white text-sm font-medium transition-all ${
            isRunning
              ? "bg-red-600 hover:bg-red-500" // Pause
              : "bg-emerald-600 hover:bg-emerald-500" // Run
          }`}
        >
          {isRunning ? "Pause" : "Run"}
        </button>
      </div>

      {err && (
        <div className="text-sm bg-red-200 border border-red-400 text-red-800 p-2 rounded">
          {err}
        </div>
      )}

      {/* GAUGES */}
      <div className="flex gap-10 bg-white border rounded-lg p-4 shadow-sm">
        <CircularGauge
          current={(global.active_users || []).length}
          max={MAX_USERS}
          label="Active Users"
        />
        <CircularGauge
          current={(global.running_jobs || []).length}
          max={MAX_RUNNING}
          label="Running Jobs"
        />
      </div>

      {/* TABS */}
      <div className="border-b border-gray-300 flex gap-6 text-sm">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`py-2 ${
              activeTab === t.key
                ? "border-b-2 border-emerald-600 font-semibold text-emerald-700"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* JOB TABLE */}
      <div className="bg-white border rounded-lg p-4 shadow-sm">
        {tabJobs.length === 0 ? (
          <p className="text-sm text-gray-400">No jobs in this category.</p>
        ) : (
          <table className="min-w-full text-xs border">
            <thead className="bg-gray-100 border-b text-gray-600">
              <tr>
                <th className="p-2 text-left">Job ID</th>
                <th className="p-2 text-left">User</th>
                <th className="p-2 text-left">Status</th>
                <th className="p-2 text-left">Progress</th>
                <th className="p-2 text-left">Updated</th>
              </tr>
            </thead>
            <tbody>
              {tabJobs.map((j) => (
                <tr key={j.job_id} className="border-b hover:bg-gray-50">
                  <td className="p-2 font-mono">
                    <a
                      href={`/jobs/${j.job_id}`}
                      className="text-sky-600 hover:underline"
                    >
                      {j.job_id}
                    </a>
                  </td>
                  <td className="p-2">{j.user_id}</td>

                  <td className="p-2">
                    <StatusPill status={j.status} />
                  </td>

                  <td className="p-2 w-48">
                    {j.status === "RUNNING" ? (
                      <ProgressBar percent={j.percent} />
                    ) : j.status === "SUCCESS" ? (
                      <span className="text-emerald-600 font-bold">✓</span>
                    ) : j.status === "FAILED" ? (
                      <span className="text-red-600 font-bold">✗</span>
                    ) : (
                      "-"
                    )}
                  </td>

                  <td className="p-2 text-gray-500">
                    {new Date(j.updated_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
