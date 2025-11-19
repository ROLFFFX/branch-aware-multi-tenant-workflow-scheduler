import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout.jsx";
import { UsersPage } from "./pages/UsersPage.jsx";
import { WorkflowsPage } from "./pages/WorkflowsPage.jsx";
import { WorkflowDetailPage } from "./pages/WorkflowDetailPage.jsx";
import { JobsPage } from "./pages/JobsPage.jsx";
import { UploadPage } from "./pages/UploadPage.jsx";
import { SchedulerPage } from "./pages/SchedulerPage.jsx";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/users" replace />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/workflows" element={<WorkflowsPage />} />
        <Route path="/workflows/:workflowId" element={<WorkflowDetailPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/scheduler" element={<SchedulerPage />} />
      </Routes>
    </Layout>
  );
}
