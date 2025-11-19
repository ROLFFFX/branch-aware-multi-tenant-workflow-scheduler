// ======================================================
// WorkflowDetailPage.jsx  — Restored Polished Layout
// ======================================================
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";

// Hard-coded templates (simplified — no JSON)
const JOB_TEMPLATES = [
  { id: "fake_sleep", label: "Fake Sleep (5s)" },
  { id: "wsi_metadata", label: "Initialize WSI" },
  { id: "tile_segmentation", label: "Tile Segmentation" },
];

export function WorkflowDetailPage() {
  const { workflowId } = useParams();

  const [workflow, setWorkflow] = useState(null);
  const [branches, setBranches] = useState([]);
  const [selectedBranch, setSelectedBranch] = useState(null);
  const [branchJobs, setBranchJobs] = useState([]);

  const [slides, setSlides] = useState([]);

  const [newBranchId, setNewBranchId] = useState("");
  const [jobForm, setJobForm] = useState({
    job_template_id: "",
    slide_id: "",
  });

  const [info, setInfo] = useState(null);
  const [err, setErr] = useState(null);

  // ---------------------- LOAD WORKFLOW ----------------------
  useEffect(() => {
    if (!workflowId) return;
    loadWorkflow(workflowId);
  }, [workflowId]);

  useEffect(() => {
    if (!selectedBranch) return;
    loadBranchJobs(workflowId, selectedBranch);
  }, [selectedBranch, workflowId]);

  async function loadWorkflow(id) {
    try {
      const wf = await api.getWorkflow(id);
      setWorkflow(wf);

      const brs = await api.getBranches(id);
      setBranches(brs);

      // auto-select entry branch
      if (wf.entry_branch && brs.includes(wf.entry_branch)) {
        setSelectedBranch(wf.entry_branch);
        loadBranchJobs(id, wf.entry_branch);
      } else if (brs.length > 0) {
        setSelectedBranch(brs[0]);
        loadBranchJobs(id, brs[0]);
      }

      if (wf.owner_user_id) loadSlides(wf.owner_user_id);
    } catch (e) {
      setErr(e.message);
    }
  }

  // ---------------------- LOAD BRANCH JOBS ----------------------
  async function loadBranchJobs(wfId, branchId) {
    try {
      const data = await api.getBranchJobs(wfId, branchId);
      setBranchJobs(data.jobs || []);
    } catch (e) {
      setErr(e.message);
    }
  }

  // ---------------------- LOAD SLIDES ----------------------
  async function loadSlides(userId) {
    try {
      const arr = await api.listSlides(userId);
      setSlides(arr || []);
    } catch {
      setSlides([]);
    }
  }

  // ---------------------- CREATE BRANCH ----------------------
  async function handleCreateBranch(e) {
    e.preventDefault();
    if (!newBranchId.trim()) return;

    try {
      await api.createBranch(workflowId, newBranchId.trim());
      setNewBranchId("");
      setInfo("Branch created.");
      loadWorkflow(workflowId);
    } catch (e) {
      setErr(e.message);
    }
  }

  // ---------------------- DELETE BRANCH ----------------------
  async function handleDeleteBranch(branchId) {
    if (!confirm(`Delete branch "${branchId}"?`)) return;

    try {
      await api.deleteBranch(workflowId, branchId);
      setInfo("Branch deleted.");
      loadWorkflow(workflowId);
      setBranchJobs([]);
      setSelectedBranch(null);
    } catch (e) {
      setErr(e.message);
    }
  }

  // ---------------------- ADD JOB ----------------------
  async function handleAddJob(e) {
    e.preventDefault();
    if (!selectedBranch) return;

    const needsSlide =
      jobForm.job_template_id === "wsi_metadata" ||
      jobForm.job_template_id === "tile_segmentation";

    const payload =
      needsSlide && jobForm.slide_id ? { slide_id: jobForm.slide_id } : {};

    try {
      await api.addBranchJob(
        workflowId,
        selectedBranch,
        jobForm.job_template_id,
        payload
      );
      setInfo("Job added.");

      // Reset form
      setJobForm({ job_template_id: "", slide_id: "" });
      loadBranchJobs(workflowId, selectedBranch);
    } catch (e) {
      setErr(e.message);
    }
  }

  // ---------------------- DELETE JOB ----------------------
  async function handleDeleteJob(index) {
    if (!confirm(`Delete job #${index + 1}?`)) return;

    try {
      await api.deleteBranchJob(workflowId, selectedBranch, index);
      setInfo("Job deleted.");
      loadBranchJobs(workflowId, selectedBranch);
    } catch (e) {
      setErr(e.message);
    }
  }

  // ---------------------- UPLOAD WSI ----------------------
  async function handleUploadWSI(e) {
    const file = e.target.files?.[0];
    if (!file || !workflow?.owner_user_id) return;

    try {
      setInfo("Uploading...");
      await api.uploadWSI(file, workflow.owner_user_id);
      setInfo("Slide uploaded.");
      loadSlides(workflow.owner_user_id);
    } catch (e) {
      setErr(e.message);
    }
  }

  if (!workflow)
    return <div className="p-8 text-gray-700">Loading workflow...</div>;

  // ================================================================
  // RENDER
  // ================================================================
  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------ */}
      {/* HEADER */}
      {/* ------------------------------------------------------ */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Workflow:{" "}
            <span className="font-mono text-sm text-sky-300">{workflowId}</span>
          </h2>

          <p className="text-xs text-gray-500">
            Name:{" "}
            <span className="font-medium text-gray-700">{workflow.name}</span> ·
            Owner: <span className="font-mono">{workflow.owner_user_id}</span> ·
            Entry branch:{" "}
            <span className="font-mono">{workflow.entry_branch ?? "—"}</span>
          </p>
        </div>

        <button
          onClick={async () => {
            try {
              setInfo("Executing workflow...");
              const res = await api.executeWorkflow(workflowId);

              // optional: refresh branch jobs (reflect new PENDING jobs)
              await loadBranchJobs(workflowId, selectedBranch);

              // display toast
              setInfo(
                "Workflow executed. Jobs moved to Pending. Run them in Scheduler page →"
              );

              // auto-clear after 5 seconds
              setTimeout(() => setInfo(null), 5000);
            } catch (e) {
              setErr("Failed to execute workflow: " + e.message);
              setTimeout(() => setErr(null), 5000);
            }
          }}
          className="px-4 py-2 rounded-md bg-emerald-600 hover:bg-emerald-500 text-sm font-medium text-white"
        >
          Execute workflow
        </button>
      </div>

      {/* Global messages */}
      {err && (
        <div className="text-xs text-red-400 bg-red-900/30 border border-red-700 rounded-md px-3 py-2">
          {err}
        </div>
      )}
      {info && (
        <div
          className="
    text-xs
    text-gray-700
    bg-green-100
    backdrop-blur-sm
    border border-gray-200
    rounded-md
    px-3 py-2
    shadow
  "
        >
          {info}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ------------------------------------------------------ */}
        {/* BRANCH LIST */}
        {/* ------------------------------------------------------ */}
        <div className="bg-white/60 border bg-gray-200 rounded-lg p-4 flex flex-col">
          <h3 className="text-sm font-medium text-gray-900 mb-3">Branches</h3>

          <div className="space-y-2 flex-1 overflow-auto">
            {branches.length === 0 ? (
              <p className="text-xs text-gray-9000">No branches yet.</p>
            ) : (
              branches.map((b) => {
                const active = selectedBranch === b;
                return (
                  <div
                    key={b}
                    className={`flex items-center justify-between px-3 py-2 rounded-md text-xs cursor-pointer border ${
                      active
                        ? "bg-white border-sky-600 text-sky-200"
                        : "bg-white bg-gray-200 text-gray-700 hover:border-slate-600"
                    }`}
                    onClick={() => setSelectedBranch(b)}
                  >
                    <span className="font-mono">{b}</span>

                    {b !== workflow.entry_branch && (
                      <button
                        className="text-[10px] px-2 py-1 rounded bg-red-700/80 hover:bg-red-600 text-red-50"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteBranch(b);
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* create branch */}
          <form
            onSubmit={handleCreateBranch}
            className="mt-3 pt-3 border-t bg-gray-200 space-y-2"
          >
            <label className="block text-xs font-medium text-slate-300">
              New branch ID
            </label>
            <input
              className="w-full px-3 py-2 rounded-md bg-white border bg-gray-300 text-xs text-gray-900"
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

        {/* ------------------------------------------------------ */}
        {/* SLIDES */}
        {/* ------------------------------------------------------ */}
        <div className="bg-white/60 border bg-gray-200 rounded-lg p-4 flex flex-col">
          <h3 className="text-sm font-medium text-gray-900 mb-3">
            Uploaded Slides
          </h3>

          <div className="space-y-2 mb-4 max-h-40 overflow-auto">
            {slides.length === 0 ? (
              <p className="text-xs text-gray-500">No slides uploaded.</p>
            ) : (
              slides.map((sl) => (
                <div
                  key={sl.slide_id}
                  className="text-xs border rounded-md p-2 bg-white"
                >
                  <div className="font-mono text-sky-700">{sl.slide_id}</div>
                  <div className="text-gray-700 text-[11px] break-all">
                    {sl.slide_path}
                  </div>
                </div>
              ))
            )}
          </div>

          <label className="block text-xs font-medium text-slate-300 mb-1">
            Upload slide (.svs)
          </label>
          <input
            type="file"
            accept=".svs"
            onChange={handleUploadWSI}
            className="text-xs"
          />
        </div>

        {/* ------------------------------------------------------ */}
        {/* JOBS */}
        {/* ------------------------------------------------------ */}
        <div className="bg-white/60 border bg-gray-200 rounded-lg p-4 lg:col-span-1 flex flex-col">
          <h3 className="text-sm font-medium text-gray-900 mb-3">
            Jobs in Branch{" "}
            <span className="font-mono text-xs text-sky-300">
              {selectedBranch ?? "—"}
            </span>
          </h3>

          <div className="space-y-2 flex-1 overflow-auto mb-4">
            {!selectedBranch ? (
              <p className="text-xs text-gray-500">
                Select a branch to view jobs.
              </p>
            ) : branchJobs.length === 0 ? (
              <p className="text-xs text-gray-500">
                No jobs yet. Add one below.
              </p>
            ) : (
              branchJobs.map((job, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between px-3 py-2 rounded-md bg-white border text-xs"
                >
                  <div>
                    <div className="font-mono text-sky-700">
                      {job.template_id}
                    </div>
                    {job.input_payload?.slide_id && (
                      <div className="text-gray-700 text-[10px]">
                        slide: {job.input_payload.slide_id}
                      </div>
                    )}
                  </div>
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

          {/* Add job */}
          <form
            onSubmit={handleAddJob}
            className="pt-3 border-t grid grid-cols-1 gap-3"
          >
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Job template
              </label>
              <select
                className="w-full px-3 py-2 rounded-md bg-white border text-xs text-gray-900"
                value={jobForm.job_template_id}
                onChange={(e) =>
                  setJobForm({
                    job_template_id: e.target.value,
                    slide_id: "",
                  })
                }
              >
                <option value="">-- choose job --</option>
                {JOB_TEMPLATES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* slide picker for jobs that need it */}
            {jobForm.job_template_id !== "" &&
              jobForm.job_template_id !== "fake_sleep" && (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Select slide
                  </label>
                  <select
                    className="w-full px-3 py-2 rounded-md bg-white border text-xs text-gray-900"
                    value={jobForm.slide_id}
                    onChange={(e) =>
                      setJobForm((f) => ({ ...f, slide_id: e.target.value }))
                    }
                  >
                    <option value="">-- choose slide --</option>
                    {slides.map((sl) => (
                      <option key={sl.slide_id} value={sl.slide_id}>
                        {sl.slide_id}
                      </option>
                    ))}
                  </select>
                </div>
              )}

            <button
              type="submit"
              disabled={
                jobForm.job_template_id === "" ||
                (jobForm.job_template_id !== "fake_sleep" &&
                  jobForm.slide_id === "")
              }
              className={`w-full px-4 py-2 rounded-md text-xs font-medium
    ${
      jobForm.job_template_id === "" ||
      (jobForm.job_template_id !== "fake_sleep" && jobForm.slide_id === "")
        ? "bg-gray-400 cursor-not-allowed text-gray-200"
        : "bg-sky-600 hover:bg-sky-500 text-white"
    }
  `}
            >
              Add Job
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
