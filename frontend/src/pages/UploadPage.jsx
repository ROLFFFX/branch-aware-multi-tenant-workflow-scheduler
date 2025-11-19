import React, { useState } from "react";
import { api } from "../api/client.js";

export function UploadPage() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState(null);
  const [result, setResult] = useState(null);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;
    try {
      setUploading(true);
      setErr(null);
      const res = await api.uploadWSI(file);
      setResult(res);
    } catch (e) {
      setErr(e.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">WSI Upload</h2>
        <p className="text-xs text-gray-500">
          Upload Aperio SVS slides to be used in workflow job payloads.
        </p>
      </div>

      <form
        onSubmit={handleUpload}
        className="bg-white/60 border bg-gray-200 rounded-lg p-6 flex flex-col gap-4 items-start"
      >
        <div className="w-full border-2 border-dashed bg-gray-300 rounded-lg p-6 text-center bg-white/40">
          <input
            id="file-input"
            type="file"
            accept=".svs"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <label htmlFor="file-input" className="cursor-pointer">
            <div className="text-sm text-gray-700">
              {file ? (
                <span className="font-medium">{file.name}</span>
              ) : (
                <span className="font-medium">Click to select a .svs file</span>
              )}
            </div>
            <div className="text-xs text-gray-9000 mt-1">
              Maximum size depends on backend / OS limits.
            </div>
          </label>
        </div>

        <button
          type="submit"
          disabled={!file || uploading}
          className={`px-4 py-2 rounded-md text-sm font-medium ${
            !file || uploading
              ? "bg-white text-gray-500 cursor-not-allowed"
              : "bg-sky-600 hover:bg-sky-500 text-white"
          }`}
        >
          {uploading ? "Uploading..." : "Upload WSI"}
        </button>
      </form>

      {err && (
        <div className="text-xs text-red-400 bg-red-900/30 border border-red-700 rounded-md px-3 py-2">
          {err}
        </div>
      )}
      {result && (
        <div className="bg-white/60 border bg-gray-200 rounded-lg p-4 text-xs">
          <div className="text-gray-500 mb-1">
            Backend response (likely a path or ID):
          </div>
          <pre className="bg-white border bg-gray-200 rounded-md p-2 font-mono text-[11px] overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
          <div className="mt-2 text-[11px] text-gray-500">
            You can paste this into job payloads in the workflow editor.
          </div>
        </div>
      )}
    </div>
  );
}
