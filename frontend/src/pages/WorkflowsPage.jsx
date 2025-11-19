import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { Link, useSearchParams } from "react-router-dom";

export function WorkflowsPage() {
  const [searchParams] = useSearchParams();
  const ownerFilter = searchParams.get("owner") || "";
  const [workflows, setWorkflows] = useState([]);
  const [form, setForm] = useState({
    workflow_id: "",
    name: "",
    owner_user_id: ownerFilter || "",
  });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  async function load() {
    try {
      setLoading(true);
      setErr(null);
      let data;
      if (ownerFilter) {
        data = await api.getWorkflowsByUser(ownerFilter);
      } else {
        data = await api.getWorkflows();
      }
      setWorkflows(Array.isArray(data) ? data : []);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [ownerFilter]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!form.workflow_id || !form.name || !form.owner_user_id) return;
    try {
      await api.createWorkflow(form);
      setForm((f) => ({ ...f, workflow_id: "", name: "" }));
      load();
    } catch (e) {
      setErr(e.message);
    }
  }

  async function handleDelete(id) {
    if (!confirm(`Delete workflow "${id}"?`)) return;
    try {
      await api.deleteWorkflow(id);
      load();
    } catch (e) {
      setErr(e.message);
    }
  }

  function updateField(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Workflows</h2>
          <p className="text-xs text-gray-500">
            Each workflow maps to branches (DAG-like) and job streams.
          </p>
        </div>
      </div>

      <form
        onSubmit={handleCreate}
        className="bg-white/60 border bg-gray-200 rounded-lg p-4 grid grid-cols-1 md:grid-cols-4 gap-3"
      >
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Workflow ID
          </label>
          <input
            className="w-full px-3 py-2 rounded-md bg-white border bg-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
            placeholder="workflow_1"
            value={form.workflow_id}
            onChange={(e) => updateField("workflow_id", e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Name
          </label>
          <input
            className="w-full px-3 py-2 rounded-md bg-white border bg-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
            placeholder="Lung slide segmentation"
            value={form.name}
            onChange={(e) => updateField("name", e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Owner user ID
          </label>
          <input
            className="w-full px-3 py-2 rounded-md bg-white border bg-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
            placeholder="user_A"
            value={form.owner_user_id}
            onChange={(e) => updateField("owner_user_id", e.target.value)}
          />
        </div>
        <div className="flex items-end">
          <button
            type="submit"
            className="w-full px-4 py-2 rounded-md bg-sky-600 hover:bg-sky-500 text-sm font-medium text-white"
          >
            Create workflow
          </button>
        </div>
      </form>

      {err && (
        <div className="text-xs text-red-400 bg-red-900/30 border border-red-700 rounded-md px-3 py-2">
          {err}
        </div>
      )}

      <div className="bg-white/60 border bg-gray-200 rounded-lg overflow-hidden">
        <div className="px-4 py-2 border-b bg-gray-200 text-xs uppercase tracking-wide text-gray-500 flex justify-between">
          <span>All Workflows</span>
          {ownerFilter && (
            <span className="text-[11px] text-gray-9000">
              filtered by owner <span className="font-mono">{ownerFilter}</span>
            </span>
          )}
        </div>
        <table className="min-w-full text-sm">
          <thead className="bg-white/80">
            <tr>
              <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">
                ID
              </th>
              <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">
                Name
              </th>
              <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">
                Owner
              </th>
              <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">
                Entry Branch
              </th>
              <th className="px-4 py-2 text-xs font-medium text-gray-500 text-right">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="px-4 py-3 text-gray-500 text-sm" colSpan={5}>
                  Loading...
                </td>
              </tr>
            ) : workflows.length === 0 ? (
              <tr>
                <td className="px-4 py-3 text-gray-9000 text-sm" colSpan={5}>
                  No workflows yet.
                </td>
              </tr>
            ) : (
              workflows.map((wf) => (
                <tr
                  key={wf.workflow_id}
                  className="border-t bg-gray-200 hover:bg-white/60"
                >
                  <td className="px-4 py-2 text-gray-900 font-mono text-xs">
                    {wf.workflow_id}
                  </td>
                  <td className="px-4 py-2 text-gray-900">{wf.name}</td>
                  <td className="px-4 py-2 text-slate-300">
                    <Link
                      to={`/workflows?owner=${encodeURIComponent(
                        wf.owner_user_id
                      )}`}
                      className="underline hover:text-sky-300 text-xs"
                    >
                      {wf.owner_user_id}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs">
                    {wf.entry_branch ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <Link
                      to={`/workflows/${wf.workflow_id}`}
                      className="text-xs px-2 py-1 rounded-md bg-white hover:bg-white text-gray-900"
                    >
                      View
                    </Link>
                    <button
                      onClick={() => handleDelete(wf.workflow_id)}
                      className="text-xs px-2 py-1 rounded-md bg-red-700/80 hover:bg-red-600 text-red-50"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
