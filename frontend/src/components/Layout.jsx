import React from "react";
import { Link, useLocation } from "react-router-dom";

const navItems = [
  { to: "/users", label: "Users" },
  { to: "/workflows", label: "Workflows" },
  { to: "/jobs", label: "Jobs" },
  //   { to: "/upload", label: "WSI Upload" },
  { to: "/scheduler", label: "Scheduler" },
];

export function Layout({ children }) {
  const location = useLocation();

  return (
    <div className="h-screen flex bg-gray-50 text-gray-900">
      {/* Sidebar */}
      <aside className="w-60 bg-gray-100 border-r border-gray-200 flex flex-col">
        <div className="px-4 py-4 border-b border-gray-200">
          <h1 className="text-lg font-semibold tracking-tight text-gray-900">
            BAMT Scheduler
          </h1>
          <p className="text-xs text-gray-500">Admin Console</p>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const active = location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center px-3 py-2 rounded-md text-sm
                  ${
                    active
                      ? "bg-white shadow-sm border border-gray-300 text-blue-600"
                      : "text-gray-700 hover:bg-gray-200 hover:text-blue-600"
                  }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* <div className="px-4 py-3 border-t border-gray-200 text-[11px] text-gray-500">
          &copy; {new Date().getFullYear()} InstanSeg / TissueLab
        </div> */}
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col">
        {/* Top bar */}
        <header className="h-14 border-b border-gray-200 px-4 flex items-center justify-between bg-white">
          <div>
            <div className="text-sm font-medium text-gray-800">
              Branch-Aware Multi-Tenant Workflow Scheduler
            </div>
            <div className="text-xs text-gray-500">
              Manage users, workflows, jobs & scheduler
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto bg-gray-50">
          <div className="p-4 md:p-6 max-w-6xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
