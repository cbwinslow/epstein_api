"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Brain,
  Play,
  Square,
  Terminal,
  Loader2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import GraphExplorer from "@/components/GraphExplorer";

interface AuditEntry {
  id: number;
  timestamp: string;
  agent_name: string;
  input_file: string | null;
  logic_reasoning: string | null;
  output_data: string | null;
  confidence_score: number | null;
  status: string;
  error_message: string | null;
}

interface SwarmStatus {
  running: boolean;
  processed: number;
  pending: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAuditLogs(limit = 50): Promise<AuditEntry[]> {
  const res = await fetch(`${API_BASE}/api/agents/audit?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch audit logs");
  return res.json();
}

async function fetchSwarmStatus(): Promise<SwarmStatus> {
  const res = await fetch(`${API_BASE}/api/agents/status`);
  if (!res.ok) throw new Error("Failed to fetch swarm status");
  return res.json();
}

async function startSwarm(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/agents/swarm/start`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to start swarm");
}

async function stopSwarm(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/agents/swarm/stop`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to stop swarm");
}

export default function AnalyzePage() {
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [swarmStatus, setSwarmStatus] = useState<SwarmStatus>({
    running: false,
    processed: 0,
    pending: 0,
  });
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const loadData = useCallback(async () => {
    try {
      const [logs, status] = await Promise.all([
        fetchAuditLogs(),
        fetchSwarmStatus(),
      ]);
      setAuditLogs(logs);
      setSwarmStatus(status);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, [loadData]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [auditLogs, autoScroll]);

  const handleStartSwarm = async () => {
    setStarting(true);
    try {
      await startSwarm();
      loadData();
    } catch (err) {
      console.error("Failed to start swarm:", err);
    } finally {
      setStarting(false);
    }
  };

  const handleStopSwarm = async () => {
    try {
      await stopSwarm();
      loadData();
    } catch (err) {
      console.error("Failed to stop swarm:", err);
    }
  };

  const formatTimestamp = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleTimeString();
  };

  const getStatusIcon = (status: string) => {
    if (status === "success") {
      return <CheckCircle className="h-4 w-4 text-emerald-400" />;
    }
    if (status === "error") {
      return <XCircle className="h-4 w-4 text-red-400" />;
    }
    return <Loader2 className="h-4 w-4 animate-spin text-amber-400" />;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Analysis & Knowledge Graph</h1>
        <p className="text-slate-400">Agent swarm control and audit trail</p>
      </div>

      {/* Swarm Control */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20">
              <Brain className="h-6 w-6 text-emerald-400" />
            </div>
            <div>
              <h2 className="font-semibold">Agent Swarm</h2>
              <p className="text-sm text-slate-400">
                Processed: {swarmStatus.processed} | Pending: {swarmStatus.pending}
              </p>
            </div>
          </div>
          {!swarmStatus.running ? (
            <button
              onClick={handleStartSwarm}
              disabled={starting}
              className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 font-medium hover:bg-emerald-700 disabled:opacity-50"
            >
              {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Awaken Swarm
            </button>
          ) : (
            <button
              onClick={handleStopSwarm}
              className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 font-medium hover:bg-red-700"
            >
              <Square className="h-4 w-4" />
              Stop Swarm
            </button>
          )}
        </div>
      </div>

      {/* Graph Explorer */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
        <h2 className="mb-4 font-semibold">Knowledge Graph Explorer</h2>
        <GraphExplorer />
      </div>

      {/* Audit Trail */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50">
        <div className="flex items-center justify-between border-b border-slate-800 p-4">
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-slate-400" />
            <h2 className="font-semibold">Audit Trail</h2>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded border-slate-700 bg-slate-800"
            />
            Auto-scroll
          </label>
        </div>
        <div className="max-h-96 overflow-auto font-mono text-xs">
          {loading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </div>
          ) : auditLogs.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-slate-400">
              No audit logs yet. Run the agent swarm to see reasoning traces.
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {auditLogs.map((entry) => (
                <div key={entry.id} className="p-3 hover:bg-slate-800/30">
                  <div className="flex items-start gap-3">
                    <span className="text-slate-500">[{formatTimestamp(entry.timestamp)}]</span>
                    <span className="font-medium text-emerald-400">{entry.agent_name}</span>
                    {getStatusIcon(entry.status)}
                  </div>
                  {entry.logic_reasoning && (
                    <div className="mt-1 text-slate-300">{entry.logic_reasoning}</div>
                  )}
                  {entry.input_file && (
                    <div className="mt-1 text-slate-500">File: {entry.input_file}</div>
                  )}
                  {entry.error_message && (
                    <div className="mt-1 text-red-400">Error: {entry.error_message}</div>
                  )}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
