import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { Link } from "react-router-dom";

export function UsersPage() {
  const [users, setUsers] = useState([]);
  const [newUserId, setNewUserId] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  async function loadUsers() {
    try {
      setLoading(true);
      setErr(null);
      const data = await api.getUsers();
      // backend returns array of strings
      setUsers(Array.isArray(data?.users) ? data.users : []);

      console.log(data);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    if (!newUserId.trim()) return;
    try {
      await api.createUser(newUserId.trim());
      setNewUserId("");
      loadUsers();
    } catch (e) {
      setErr(e.message);
    }
  }

  async function handleDelete(userId) {
    if (!confirm(`Delete user "${userId}"?`)) return;
    try {
      await api.deleteUser(userId);
      loadUsers();
    } catch (e) {
      setErr(e.message);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Users</h2>
          <p className="text-xs text-gray-500">
            Each user owns workflows and has isolated job queues.
          </p>
        </div>
      </div>

      <form
        onSubmit={handleCreate}
        className="flex flex-col sm:flex-row gap-3 bg-white/60 border bg-gray-200 rounded-lg p-4"
      >
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-300 mb-1">
            New user ID
          </label>
          <input
            className="w-full px-3 py-2 rounded-md bg-white border bg-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
            placeholder="e.g. user_A"
            value={newUserId}
            onChange={(e) => setNewUserId(e.target.value)}
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 rounded-md bg-sky-600 hover:bg-sky-500 text-sm font-medium text-white self-end"
        >
          Create user
        </button>
      </form>

      {err && (
        <div className="text-xs text-red-400 bg-red-900/30 border border-red-700 rounded-md px-3 py-2">
          {err}
        </div>
      )}

      <div className="bg-white/60 border bg-gray-200 rounded-lg overflow-hidden">
        <div className="px-4 py-2 border-b bg-gray-200 text-xs uppercase tracking-wide text-gray-500">
          Registered Users
        </div>
        <table className="min-w-full text-sm">
          <thead className="bg-white/80">
            <tr>
              <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">
                User ID
              </th>
              <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">
                Workflows
              </th>
              <th className="px-4 py-2 text-xs font-medium text-gray-500 text-right">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="px-4 py-3 text-gray-500 text-sm" colSpan={3}>
                  Loading...
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td className="px-4 py-3 text-gray-9000 text-sm" colSpan={3}>
                  No users yet. Create one above.
                </td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u} className="border-t bg-gray-200">
                  <td className="px-4 py-2 text-gray-900">{u}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">
                    <Link
                      to={`/workflows?owner=${encodeURIComponent(u)}`}
                      className="underline hover:text-sky-300"
                    >
                      View workflows
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => handleDelete(u)}
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
