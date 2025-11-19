import React, { useState, useEffect } from "react";
import { api } from "../api/client.js";

export function JobsPage() {
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  // Load available job templates
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

  async function runTemplate(template) {
    // Use a small fake payload
    const defaultPayload = { seconds: 3 };

    try {
      setCreating(true);
      setErr(null);

      // Your backend needs: create job -> returns { job_id }
      const newJob = await api.createJob({
        job_template_id: template,
        input_payload: defaultPayload,
      });

      setJobId(newJob.job_id);

      // immediately fetch the created job
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

      {/* Job Templates Section */}
      <div className="bg-white/60 border bg-gray-200 rounded-lg p-4 space-y-2">
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

      {/* Job Fetch Form */}
      <form
        onSubmit={handleFetch}
        className="bg-white/60 border bg-gray-200 rounded-lg p-4 flex flex-col sm:flex-row gap-3"
      >
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Job ID
          </label>
          <input
            className="w-full px-3 py-2 rounded-md bg-white border bg-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
            placeholder="paste job id"
            value={jobId}
            onChange={(e) => setJobId(e.target.value)}
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 rounded-md bg-sky-600 hover:bg-sky-500 text-sm font-medium text-white self-end"
        >
          Fetch job
        </button>
      </form>

      {err && (
        <div className="text-xs text-red-400 bg-red-900/30 border border-red-700 rounded-md px-3 py-2">
          {err}
        </div>
      )}

      {loading && <div className="text-xs text-gray-500">Loading job...</div>}

      {job && <JobDetails job={job} />}
    </div>
  );
}

function JobDetails({ job }) {
  return (
    <div className="bg-white/60 border bg-gray-200 rounded-lg p-4 space-y-3 text-xs">
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Payload label="Input payload" data={job.input_payload} />
        <Payload label="Output payload" data={job.output_payload} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Timestamp label="Created" value={job.created_at} />
        <Timestamp label="Scheduled" value={job.scheduled_at} />
        <Timestamp label="Started" value={job.started_at} />
        <Timestamp label="Finished" value={job.finished_at} />
      </div>
    </div>
  );
}

function Info({ label, value, mono }) {
  return (
    <div>
      <div className="text-gray-500">{label}</div>
      <div className={`text-gray-700 text-xs ${mono ? "font-mono" : ""}`}>
        {value ?? "—"}
      </div>
    </div>
  );
}

function Payload({ label, data }) {
  return (
    <div>
      <div className="text-gray-500 mb-1">{label}</div>
      <pre className="bg-white border bg-gray-200 rounded-md p-2 text-[11px] overflow-auto">
        {JSON.stringify(data || {}, null, 2)}
      </pre>
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
