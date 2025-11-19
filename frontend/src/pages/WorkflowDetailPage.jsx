import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";

// OPTIONAL: auto-suggest payloads depending on template
const TEMPLATE_PAYLOAD_SUGGESTIONS = {
  fake_sleep: '{\n  "seconds": 5\n}',
  generate_tissue_mask: '{\n  "wsi_path": "path/to/wsi.svs"\n}',
  segment_cells: '{\n  "mask_path": "path/to/mask.tif"\n}',
  export_polygons: '{\n  "cells_path": "path/to/cells.json"\n}',
};

export function WorkflowDetailPage() {
  const { workflowId } = useParams();

  const [workflow, setWorkflow] = useState(null);
  const [branches, setBranches] = useState([]);
  const [selectedBranchId, setSelectedBranchId] = useState(null);
  const [branchJobs, setBranchJobs] = useState([]);

  const [jobTemplates, setJobTemplates] = useState([]);

  const [newBranchId, setNewBranchId] = useState("");

  const [jobForm, setJobForm] = useState({
    job_template_id: "",
    payloadJson: "{}",
  });

  const [err, setErr] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);

  // ----------- Load job templates from backend ----------- //
  useEffect(() => {
    async function loadTemplates() {
      try {
        const arr = await api.listJobTemplates(); // GET /jobs/job-templates
        // arr = ["fake_sleep", "generate_tissue_mask", ...]
        const formatted = arr.map((id) => ({
          id,
          label: id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        }));

        setJobTemplates(formatted);

        // set default template + default payload
        setJobForm((f) => ({
          ...f,
          job_template_id: formatted[0]?.id || "",
          payloadJson: TEMPLATE_PAYLOAD_SUGGESTIONS[formatted[0]?.id] || "{}",
        }));
      } catch (e) {
        console.error("Failed to load job templates:", e);
      }
    }
    loadTemplates();
  }, []);

  // ----------- Load workflow + branches ----------- //
  async function loadWorkflow() {
    try {
      setLoading(true);
      setErr(null);

      const wf = await api.getWorkflow(workflowId);
      setWorkflow(wf);

      const brs = await api.getBranches(workflowId);
      setBranches(Array.isArray(brs) ? brs : []);

      // auto-select first branch
      if (brs?.length && !selectedBranchId) {
        setSelectedBranchId(brs[0]);
      }
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadBranchJobs(branchId) {
    if (!branchId) return;
    try {
      const res = await api.getBranchJobs(workflowId, branchId);
      setBranchJobs(res.jobs || []);
    } catch (e) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    loadWorkflow();
  }, [workflowId]);

  useEffect(() => {
    if (selectedBranchId) {
      loadBranchJobs(selectedBranchId);
    } else {
      setBranchJobs([]);
    }
  }, [selectedBranchId]);

  // ----------- Create branch ----------- //
  async function handleCreateBranch(e) {
    e.preventDefault();
    if (!newBranchId.trim()) return;
    try {
      await api.createBranch(workflowId, newBranchId.trim());
      setNewBranchId("");
      setInfo("Branch created.");
      loadWorkflow();
    } catch (e) {
      setErr(e.message);
    }
  }

  // ----------- Append job ----------- //
  async function handleAddJob(e) {
    e.preventDefault();
    if (!selectedBranchId) {
      setErr("Select a branch first.");
      return;
    }
    let payload;
    try {
      payload = JSON.parse(jobForm.payloadJson || "{}");
    } catch {
      setErr("Payload JSON is invalid.");
      return;
    }
    try {
      await api.addBranchJob(
        workflowId,
        selectedBranchId,
        jobForm.job_template_id,
        payload
      );
      setInfo("Job appended to branch.");
      loadBranchJobs(selectedBranchId);
    } catch (e) {
      setErr(e.message);
    }
  }

  // ----------- Delete branch ----------- //
  async function handleDeleteBranch(branchId) {
    if (!confirm(`Delete branch "${branchId}"?`)) return;
    try {
      await api.deleteBranch(workflowId, branchId);
      setInfo("Branch deleted.");
      if (selectedBranchId === branchId) {
        setSelectedBranchId(null);
        setBranchJobs([]);
      }
      loadWorkflow();
    } catch (e) {
      setErr(e.message);
    }
  }

  // ----------- Job branch ----------- //
  async function handleDeleteJob(index) {
    if (!selectedBranchId) return;

    if (!confirm(`Delete job #${index + 1}?`)) return;

    try {
      setErr(null);
      await api.deleteBranchJob(workflowId, selectedBranchId, index);
      await loadBranchJobs(selectedBranchId);
    } catch (e) {
      setErr(e.message);
    }
  }

  // ----------- Execute workflow ----------- //
  async function handleExecuteWorkflow() {
    try {
      await api.executeWorkflow(workflowId);
      setInfo("Workflow execution started.");
    } catch (e) {
      setErr(e.message);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Workflow:{" "}
            <span className="font-mono text-sm text-sky-300">{workflowId}</span>
          </h2>
          {workflow && (
            <p className="text-xs text-gray-500">
              Name:{" "}
              <span className="font-medium text-gray-700">{workflow.name}</span>{" "}
              · Owner:{" "}
              <span className="font-mono">{workflow.owner_user_id}</span> ·
              Entry branch:{" "}
              <span className="font-mono">{workflow.entry_branch ?? "—"}</span>
            </p>
          )}
        </div>
        <button
          onClick={handleExecuteWorkflow}
          className="px-4 py-2 rounded-md bg-emerald-600 hover:bg-emerald-500 text-sm font-medium text-white"
        >
          Execute workflow
        </button>
      </div>

      {err && (
        <div className="text-xs text-red-400 bg-red-900/30 border border-red-700 rounded-md px-3 py-2">
          {err}
        </div>
      )}
      {info && (
        <div className="text-xs text-emerald-400 bg-emerald-900/20 border border-emerald-700 rounded-md px-3 py-2">
          {info}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Branch List */}
        <div className="bg-white/60 border bg-gray-200 rounded-lg p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900">Branches</h3>
          </div>

          <div className="space-y-2 flex-1 overflow-auto">
            {loading ? (
              <p className="text-xs text-gray-500">Loading...</p>
            ) : branches.length === 0 ? (
              <p className="text-xs text-gray-9000">
                No branches yet. Create one below.
              </p>
            ) : (
              branches.map((b) => {
                const active = selectedBranchId === b;
                return (
                  <div
                    key={b}
                    className={`flex items-center justify-between px-3 py-2 rounded-md text-xs cursor-pointer border
                      ${
                        active
                          ? "bg-white border-sky-600 text-sky-200"
                          : "bg-white bg-gray-200 text-gray-700 hover:border-slate-600"
                      }`}
                    onClick={() => setSelectedBranchId(b)}
                  >
                    <span className="font-mono">{b}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteBranch(b);
                      }}
                      className="text-[10px] px-2 py-1 rounded bg-red-700/80 hover:bg-red-600 text-red-50"
                    >
                      Delete
                    </button>
                  </div>
                );
              })
            )}
          </div>

          <form
            onSubmit={handleCreateBranch}
            className="mt-3 pt-3 border-t bg-gray-200 space-y-2"
          >
            <label className="block text-xs font-medium text-slate-300">
              New branch ID
            </label>
            <input
              className="w-full px-3 py-2 rounded-md bg-white border bg-gray-300 text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="branch_A"
              value={newBranchId}
              onChange={(e) => setNewBranchId(e.target.value)}
            />
            <button
              type="submit"
              className="w-full px-3 py-2 rounded-md bg-sky-600 hover:bg-sky-500 text-xs font-medium text-white"
            >
              Create branch
            </button>
          </form>
        </div>

        {/* Jobs In Branch */}
        <div className="bg-white/60 border bg-gray-200 rounded-lg p-4 lg:col-span-2 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900">
              Jobs in branch{" "}
              <span className="font-mono text-xs text-sky-300">
                {selectedBranchId ?? "—"}
              </span>
            </h3>
          </div>

          <div className="space-y-2 flex-1 overflow-auto">
            {!selectedBranchId ? (
              <p className="text-xs text-gray-9000">
                Select a branch to view jobs.
              </p>
            ) : branchJobs.length === 0 ? (
              <p className="text-xs text-gray-9000">
                No jobs yet. Append a job below.
              </p>
            ) : (
              branchJobs.map((job, idx) => (
                <div
                  key={`${idx}-${job.template_id}`}
                  className="flex flex-col md:flex-row md:items-center justify-between gap-2 px-3 py-2 rounded-md bg-white border bg-gray-200 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-white text-[10px] font-medium text-gray-700">
                      {idx + 1}
                    </span>
                    <div>
                      <div className="font-mono text-sky-200">
                        {job.template_id}
                      </div>
                      <div className="text-[10px] text-gray-9000 truncate max-w-xs">
                        payload:{" "}
                        <span className="font-mono">
                          {JSON.stringify(job.input_payload)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Delete button */}
                  <button
                    onClick={() => handleDeleteJob(idx)}
                    className="text-[10px] px-2 py-1 rounded bg-red-700/80 hover:bg-red-600 text-red-50"
                  >
                    Delete
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Add Job Form */}
          <form
            onSubmit={handleAddJob}
            className="mt-3 pt-3 border-t bg-gray-200 grid grid-cols-1 md:grid-cols-2 gap-3"
          >
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Job template
              </label>
              <select
                className="w-full px-3 py-2 rounded-md bg-white border bg-gray-300 text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
                value={jobForm.job_template_id}
                onChange={(e) => {
                  const tmpl = e.target.value;
                  setJobForm((f) => ({
                    ...f,
                    job_template_id: tmpl,
                    payloadJson: TEMPLATE_PAYLOAD_SUGGESTIONS[tmpl] || "{}",
                  }));
                }}
              >
                {jobTemplates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:row-span-2">
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Input payload (JSON)
              </label>
              <textarea
                className="w-full h-28 px-3 py-2 rounded-md bg-white border bg-gray-300 text-xs text-gray-900 font-mono resize-none focus:outline-none focus:ring-1 focus:ring-sky-500"
                value={jobForm.payloadJson}
                onChange={(e) =>
                  setJobForm((f) => ({ ...f, payloadJson: e.target.value }))
                }
              />
            </div>

            <div className="flex items-end">
              <button
                type="submit"
                className="w-full px-4 py-2 rounded-md bg-sky-600 hover:bg-sky-500 text-xs font-medium text-white"
              >
                Append job to branch
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
