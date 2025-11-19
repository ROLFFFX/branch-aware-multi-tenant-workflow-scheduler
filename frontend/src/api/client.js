const API_BASE = "http://localhost:8000";

async function request(path, { method = "GET", body, headers = {} } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }

  try {
    return await res.json();
  } catch {
    return null; // some endpoints return plain string
  }
}

export const api = {
  // Users
  getUsers: () => request("/users/"),
  createUser: (user_id) =>
    request("/users/", { method: "POST", body: { user_id } }),
  deleteUser: (user_id) => request(`/users/${user_id}`, { method: "DELETE" }),

  // Workflows
  getWorkflows: () => request("/workflows/"),
  createWorkflow: ({ workflow_id, name, owner_user_id }) =>
    request("/workflows/", {
      method: "POST",
      body: { workflow_id, name, owner_user_id },
    }),
  deleteWorkflow: (workflow_id) =>
    request(`/workflows/${workflow_id}`, { method: "DELETE" }),
  getWorkflow: (workflow_id) => request(`/workflows/${workflow_id}`),
  getWorkflowsByUser: (user_id) => request(`/workflows/by_user/${user_id}`),

  // Branches
  getBranches: (workflow_id) => request(`/workflows/${workflow_id}/branches`),
  createBranch: (workflow_id, branch_id) =>
    request(`/workflows/${workflow_id}/branches`, {
      method: "POST",
      body: { branch_id },
    }),
  getBranchJobs: (workflow_id, branch_id) =>
    request(`/workflows/${workflow_id}/branches/${branch_id}`),
  addBranchJob: (workflow_id, branch_id, job_template_id, input_payload) =>
    request(`/workflows/${workflow_id}/branches/${branch_id}/jobs`, {
      method: "POST",
      body: { job_template_id, input_payload },
    }),
  deleteBranch: (workflow_id, branch_id) =>
    request(`/workflows/${workflow_id}/branches/${branch_id}`, {
      method: "DELETE",
    }),

  // Jobs
  getJob: (job_id) => request(`/jobs/${job_id}`),
  listJobTemplates: () => request("/jobs/job-templates"),
  deleteBranchJob: (workflow_id, branch_id, index) =>
    request(`/workflows/${workflow_id}/branches/${branch_id}/jobs/${index}`, {
      method: "DELETE",
    }),

  // Execution / Scheduler
  executeWorkflow: (workflow_id) =>
    request(`/workflows/${workflow_id}/execute`, { method: "POST" }),
  startScheduler: () => request("/scheduler/start", { method: "POST" }),
  pauseScheduler: () => request("/scheduler/pause", { method: "POST" }),
  getSchedulerState: () => request("/scheduler/state"),

  // Files
  uploadWSI: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/files/upload_wsi`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    try {
      return await res.json();
    } catch {
      return null;
    }
  },
};
