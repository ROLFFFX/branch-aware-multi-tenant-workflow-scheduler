// ======================================================
// JobsPage.jsx — Fully Patched With Working Downloads
// ======================================================
import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";

// ----------------------------------------------
// Backend base URL for downloads
// ----------------------------------------------
const BACKEND = "http://127.0.0.1:8000";

// ------------------------------------------------------
// File path detection helper
// ------------------------------------------------------
function isFilePath(value) {
  if (typeof value !== "string") return false;
  const lower = value.toLowerCase();

  return (
    lower.includes("/tmp/") ||
    lower.includes("/storage/") ||
    lower.endsWith(".png") ||
    lower.endsWith(".jpg") ||
    lower.endsWith(".jpeg") ||
    lower.endsWith(".tiff") ||
    lower.endsWith(".tif") ||
    lower.endsWith(".svs") ||
    lower.endsWith(".json") ||
    lower.endsWith(".mask") ||
    lower.endsWith(".npy")
  );
}

function makeDownloadUrl(path) {
  const clean = String(path).replace(/^"|"$/g, "");
  return `${BACKEND}/files/download?path=${encodeURIComponent(clean)}`;
}

// ------------------------------------------------------
// File-aware Output Renderer (FINAL VERSION)
// ------------------------------------------------------
function RenderOutput({ data }) {
  let parsed = data;

  try {
    parsed = JSON.parse(data);
  } catch {
    /* leave parsed as-is */
  }

  // Object: display each key/value
  if (typeof parsed === "object" && parsed !== null) {
    return (
      <div className="space-y-1 text-[11px]">
        {Object.entries(parsed).map(([key, value]) => (
          <div key={key}>
            <div className="text-gray-600 font-semibold">{key}:</div>

            {isFilePath(value) ? (
              <a
                href={makeDownloadUrl(value)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-600 underline hover:text-sky-500 ml-1"
              >
                Download {String(value).split("/").pop()}
              </a>
            ) : (
              <pre className="bg-white border rounded-md p-2 overflow-auto">
                {JSON.stringify(value, null, 2)}
              </pre>
            )}
          </div>
        ))}
      </div>
    );
  }

  // Single file path
  if (isFilePath(parsed)) {
    return (
      <a
        href={makeDownloadUrl(parsed)}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sky-600 underline hover:text-sky-500"
      >
        Download {String(parsed).split("/").pop()}
      </a>
    );
  }

  // Fallback text
  return (
    <pre className="bg-white border rounded-md p-2 overflow-auto">
      {String(parsed)}
    </pre>
  );
}

// ======================================================
// Main JobsPage Component
// ======================================================
export function JobsPage() {
  const { jobId: urlJobId } = useParams();

  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  // Load job templates
  useEffect(() => {
    async function loadTemplates() {
      try {
        const t = await api.listJobTemplates();
        setTemplates(Array.isArray(t) ? t : []);
      } catch (e) {
        console.error("Failed to load templates:", e);
      }
    }
    loadTemplates();
  }, []);

  // Auto-load job if URL contains ID
  useEffect(() => {
    if (!urlJobId) return;
    setJobId(urlJobId);

    async function loadJob() {
      try {
        const data = await api.getJob(urlJobId);
        setJob(data);
        setErr(null);
      } catch (e) {
        setErr(e.message);
        setJob(null);
      }
    }
    loadJob();
  }, [urlJobId]);

  // Manual fetch by ID
  async function handleFetch(e) {
    e.preventDefault();
    if (!jobId.trim()) return;

    try {
      setLoading(true);
      setErr(null);
      const data = await api.getJob(jobId.trim());
      setJob(data);
    } catch (e) {
      setErr(e.message);
      setJob(null);
    } finally {
      setLoading(false);
    }
  }

  // Run a job template
  async function runTemplate(template) {
    const defaultPayload = { seconds: 3 };

    try {
      setCreating(true);
      setErr(null);

      const newJob = await api.createJob({
        job_template_id: template,
        input_payload: defaultPayload,
      });

      setJobId(newJob.job_id);

      const data = await api.getJob(newJob.job_id);
      setJob(data);
    } catch (e) {
      setErr(e.message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Jobs</h2>
        <p className="text-xs text-gray-500">
          Select a predefined job template, or manually lookup a job by ID.
        </p>
      </div>

      {/* Job Templates */}
      <div className="bg-white border rounded-lg p-4 space-y-2">
        <div className="text-xs text-gray-500 uppercase font-semibold">
          Available Job Templates
        </div>

        {templates.length === 0 ? (
          <div className="text-xs text-gray-500">No templates</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {templates.map((t) => (
              <button
                key={t}
                onClick={() => runTemplate(t)}
                disabled={creating}
                className="px-3 py-1 text-xs rounded-md bg-sky-600 text-white hover:bg-sky-500 disabled:opacity-50"
              >
                Run: {t}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Job ID search */}
      <form
        onSubmit={handleFetch}
        className="bg-white border rounded-lg p-4 flex flex-col sm:flex-row gap-3"
      >
        <div className="flex-1">
          <label className="block text-xs text-gray-600 mb-1">Job ID</label>
          <input
            className="w-full px-3 py-2 rounded-md bg-white border text-sm text-gray-900"
            value={jobId}
            onChange={(e) => setJobId(e.target.value)}
          />
        </div>

        <button
          type="submit"
          className="px-4 py-2 rounded-md bg-sky-600 text-white hover:bg-sky-500"
        >
          Fetch job
        </button>
      </form>

      {err && (
        <div className="text-xs text-red-500 bg-red-100 border border-red-300 rounded p-2">
          {err}
        </div>
      )}

      {loading && <div className="text-xs text-gray-500">Loading job…</div>}

      {job && <JobDetails job={job} />}
    </div>
  );
}

// ======================================================
// JobDetails Component
// ======================================================
function JobDetails({ job }) {
  return (
    <div className="bg-white border rounded-lg p-4 space-y-3 text-xs">
      <div className="flex flex-wrap gap-4">
        <Info label="Job ID" value={job.job_id} mono />
        <Info label="Status" value={job.status} />
        <Info label="Template" value={job.job_template_id} mono />
        <Info
          label="Workflow / Branch"
          value={`${job.workflow_id} / ${job.branch_id}`}
          mono
        />
        <Info label="User" value={job.user_id} mono />
      </div>

      {/* Input + Output */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Payload label="Input payload" data={job.input_payload} />
        <Payload label="Output payload" data={job.output_payload} />
      </div>

      {/* Timestamps */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Timestamp label="Created" value={job.created_at} />
        <Timestamp label="Scheduled" value={job.scheduled_at} />
        <Timestamp label="Started" value={job.started_at} />
        <Timestamp label="Finished" value={job.finished_at} />
      </div>
    </div>
  );
}

// ------------------------------------------------------
// Helper UI Components
// ------------------------------------------------------
function Info({ label, value, mono }) {
  return (
    <div>
      <div className="text-gray-500">{label}</div>
      <div className={`text-gray-800 text-xs ${mono ? "font-mono" : ""}`}>
        {value ?? "—"}
      </div>
    </div>
  );
}

function Payload({ label, data }) {
  return (
    <div>
      <div className="text-gray-500 mb-1">{label}</div>
      <RenderOutput data={data} />
    </div>
  );
}

function Timestamp({ label, value }) {
  return (
    <div>
      <div className="text-gray-500">{label}</div>
      <div className="font-mono text-[11px] text-gray-700">{value ?? "—"}</div>
    </div>
  );
}
