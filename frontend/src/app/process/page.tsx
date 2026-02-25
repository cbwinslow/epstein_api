"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FileText,
  Image,
  Mic,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Play,
} from "lucide-react";

interface QueueStats {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  by_type: {
    ocr: number;
    text_extraction: number;
    transcription: number;
  };
}

interface FailedFile {
  id: number;
  filename: string;
  error: string;
  retry_count: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchQueueStats(): Promise<QueueStats> {
  const res = await fetch(`${API_BASE}/api/queue/stats`);
  if (!res.ok) throw new Error("Failed to fetch queue stats");
  return res.json();
}

async function fetchFailedFiles(): Promise<FailedFile[]> {
  const res = await fetch(`${API_BASE}/api/queue/failed`);
  if (!res.ok) throw new Error("Failed to fetch failed files");
  return res.json();
}

async function retryWithOcr(fileId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/queue/retry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_id: fileId, force_ocr: true }),
  });
  if (!res.ok) throw new Error("Failed to retry file");
}

export default function ProcessPage() {
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [failed, setFailed] = useState<FailedFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [statsData, failedData] = await Promise.all([
        fetchQueueStats(),
        fetchFailedFiles(),
      ]);
      setStats(statsData);
      setFailed(failedData);
    } catch (err) {
      console.error("Failed to load queue data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleRetry = async (fileId: number) => {
    setRetrying(fileId);
    try {
      await retryWithOcr(fileId);
      loadData();
    } catch (err) {
      console.error("Failed to retry:", err);
    } finally {
      setRetrying(null);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Processing Queue</h1>
        <p className="text-slate-400">Monitor ETL pipeline and queued tasks</p>
      </div>

      {/* Queue Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          title="Pending"
          value={stats?.pending ?? 0}
          icon={FileText}
          color="blue"
        />
        <StatCard
          title="Processing"
          value={stats?.processing ?? 0}
          icon={Loader2}
          color="amber"
          spin
        />
        <StatCard
          title="Completed"
          value={stats?.completed ?? 0}
          icon={CheckCircle}
          color="emerald"
        />
        <StatCard
          title="Failed"
          value={stats?.failed ?? 0}
          icon={AlertTriangle}
          color="red"
        />
      </div>

      {/* By Type */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
        <h2 className="mb-4 font-semibold">Queue by Type</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <QueueTypeCard
            type="OCR"
            count={stats?.by_type.ocr ?? 0}
            icon={Image}
          />
          <QueueTypeCard
            type="Text Extraction"
            count={stats?.by_type.text_extraction ?? 0}
            icon={FileText}
          />
          <QueueTypeCard
            type="Transcription"
            count={stats?.by_type.transcription ?? 0}
            icon={Mic}
          />
        </div>
      </div>

      {/* Failed Files */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50">
        <div className="border-b border-slate-800 p-4">
          <h2 className="font-semibold">Failed Files (Manual Override)</h2>
        </div>
        {failed.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            No failed files. All processing completed successfully.
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {failed.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-4"
              >
                <div className="flex-1 min-w-0">
                  <p className="truncate font-medium">{file.filename}</p>
                  <p className="text-sm text-red-400 truncate">{file.error}</p>
                  <p className="text-xs text-slate-500">
                    Retries: {file.retry_count}
                  </p>
                </div>
                <button
                  onClick={() => handleRetry(file.id)}
                  disabled={retrying === file.id}
                  className="ml-4 flex items-center gap-2 rounded-lg bg-amber-600 px-3 py-2 text-sm hover:bg-amber-700 disabled:opacity-50"
                >
                  {retrying === file.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  OCR Fallback
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex justify-end">
        <button
          onClick={loadData}
          className="flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  spin,
}: {
  title: string;
  value: number;
  icon: React.ElementType;
  color: "blue" | "amber" | "emerald" | "red";
  spin?: boolean;
}) {
  const colors = {
    blue: "text-blue-400 bg-blue-500/10",
    amber: "text-amber-400 bg-amber-500/10",
    emerald: "text-emerald-400 bg-emerald-500/10",
    red: "text-red-400 bg-red-500/10",
  };

  return (
    <div className={`rounded-lg border border-slate-800 p-4 ${colors[color]}`}>
      <div className="flex items-center gap-3">
        <Icon className={`h-5 w-5 ${spin ? "animate-spin" : ""}`} />
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs opacity-70">{title}</p>
        </div>
      </div>
    </div>
  );
}

function QueueTypeCard({
  type,
  count,
  icon: Icon,
}: {
  type: string;
  count: number;
  icon: React.ElementType;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-800/50 p-3">
      <div className="flex items-center gap-3">
        <Icon className="h-5 w-5 text-slate-400" />
        <span className="text-sm">{type}</span>
      </div>
      <span className="font-bold">{count}</span>
    </div>
  );
}
