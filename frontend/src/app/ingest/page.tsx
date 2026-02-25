"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  Trash2,
  Upload,
  X,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
} from "lucide-react";
import {
  fetchDownloads,
  addUrls,
  startQueue,
  pauseQueue,
  resumeQueue,
  cancelDownload,
  createWebSocket,
  DownloadTask,
  DownloadProgress,
} from "@/lib/api";

export default function IngestPage() {
  const [urls, setUrls] = useState("");
  const [tasks, setTasks] = useState<DownloadTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [queueRunning, setQueueRunning] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const loadTasks = useCallback(async () => {
    try {
      const data = await fetchDownloads();
      setTasks(data);
    } catch (err) {
      console.error("Failed to load downloads:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();

    const ws = createWebSocket();
    wsRef.current = ws;

    ws.onopen = () => console.log("WebSocket connected");
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "progress") {
          const progress: DownloadProgress = data.payload;
          setTasks((prev) =>
            prev.map((t) =>
              t.id === progress.task_id
                ? { ...t, progress: progress.progress, speed: progress.speed, eta: progress.eta }
                : t
            )
          );
        } else if (data.type === "status") {
          setQueueRunning(data.payload.running);
          loadTasks();
        }
      } catch (err) {
        console.error("WebSocket message error:", err);
      }
    };

    ws.onerror = (err) => console.error("WebSocket error:", err);
    ws.onclose = () => console.log("WebSocket disconnected");

    return () => {
      ws.close();
    };
  }, [loadTasks]);

  const handleSubmit = async () => {
    const urlList = urls
      .split("\n")
      .map((u) => u.trim())
      .filter((u) => u.length > 0);

    if (urlList.length === 0) return;

    setSubmitting(true);
    try {
      await addUrls(urlList);
      setUrls("");
      loadTasks();
    } catch (err) {
      console.error("Failed to add URLs:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleStart = async () => {
    try {
      await startQueue();
      setQueueRunning(true);
    } catch (err) {
      console.error("Failed to start queue:", err);
    }
  };

  const handlePause = async () => {
    try {
      await pauseQueue();
      setQueueRunning(false);
    } catch (err) {
      console.error("Failed to pause queue:", err);
    }
  };

  const handleResume = async () => {
    try {
      await resumeQueue();
      setQueueRunning(true);
    } catch (err) {
      console.error("Failed to resume queue:", err);
    }
  };

  const handleCancel = async (id: number) => {
    try {
      await cancelDownload(id);
      loadTasks();
    } catch (err) {
      console.error("Failed to cancel:", err);
    }
  };

  const statusIcon = (status: DownloadTask["status"]) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-emerald-400" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-400" />;
      case "downloading":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-400" />;
      case "paused":
        return <Clock className="h-4 w-4 text-amber-400" />;
      default:
        return <Clock className="h-4 w-4 text-slate-400" />;
    }
  };

  const formatSpeed = (bytesPerSec?: number) => {
    if (!bytesPerSec) return "-";
    if (bytesPerSec < 1024) return `${bytesPerSec} B/s`;
    if (bytesPerSec < 1024 * 1024) return `${(bytesPerSec / 1024).toFixed(1)} KB/s`;
    return `${(bytesPerSec / 1024 / 1024).toFixed(1)} MB/s`;
  };

  const formatEta = (seconds?: number) => {
    if (!seconds) return "-";
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Ingest & Download Manager</h1>
        <p className="text-slate-400">Add DOJ/Epstein file URLs for download</p>
      </div>

      {/* URL Input */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
        <label className="mb-2 block text-sm font-medium">
          Add URLs (one per line)
        </label>
        <textarea
          value={urls}
          onChange={(e) => setUrls(e.target.value)}
          placeholder="https://example.com/file1.pdf&#10;https://example.com/file2.pdf"
          className="min-h-[120px] w-full rounded-lg border border-slate-700 bg-slate-800 p-3 text-sm text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none"
        />
        <div className="mt-3 flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={submitting || !urls.trim()}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            <Upload className="h-4 w-4" />
            {submitting ? "Adding..." : "Add URLs"}
          </button>
        </div>
      </div>

      {/* Control Panel */}
      <div className="flex items-center gap-3">
        {!queueRunning ? (
          <button
            onClick={handleStart}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-700"
          >
            <Play className="h-4 w-4" />
            Start Queue
          </button>
        ) : (
          <button
            onClick={handlePause}
            className="flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium hover:bg-amber-700"
          >
            <Pause className="h-4 w-4" />
            Pause All
          </button>
        )}
        <button
          onClick={handleResume}
          disabled={!tasks.some((t) => t.status === "paused")}
          className="flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          <RotateCcw className="h-4 w-4" />
          Resume All
        </button>
      </div>

      {/* Download Ledger */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50">
        <div className="border-b border-slate-800 p-4">
          <h2 className="font-semibold">Download Ledger</h2>
        </div>
        <div className="max-h-[400px] overflow-auto">
          {loading ? (
            <div className="p-8 text-center text-slate-400">
              <Loader2 className="mx-auto h-6 w-6 animate-spin" />
            </div>
          ) : tasks.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              No downloads yet. Add URLs above to get started.
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-slate-800/50 text-left text-xs uppercase text-slate-400">
                <tr>
                  <th className="p-3">Status</th>
                  <th className="p-3">File</th>
                  <th className="p-3">Progress</th>
                  <th className="p-3">Speed</th>
                  <th className="p-3">ETA</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {tasks.map((task) => (
                  <tr key={task.id} className="hover:bg-slate-800/30">
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        {statusIcon(task.status)}
                        <span className="text-sm capitalize">{task.status}</span>
                      </div>
                    </td>
                    <td className="p-3 max-w-[200px] truncate text-sm" title={task.filename}>
                      {task.filename}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-700">
                          <div
                            className="h-full bg-emerald-500 transition-all"
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-400">{task.progress}%</span>
                      </div>
                    </td>
                    <td className="p-3 text-sm text-slate-400">{formatSpeed(task.speed)}</td>
                    <td className="p-3 text-sm text-slate-400">{formatEta(task.eta)}</td>
                    <td className="p-3">
                      <button
                        onClick={() => handleCancel(task.id)}
                        className="rounded p-1 hover:bg-slate-700"
                        title="Cancel"
                      >
                        <Trash2 className="h-4 w-4 text-slate-400" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
