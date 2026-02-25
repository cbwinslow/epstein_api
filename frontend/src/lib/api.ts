const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface DownloadTask {
  id: number;
  url: string;
  filename: string;
  status: "pending" | "downloading" | "completed" | "failed" | "paused";
  progress: number;
  speed?: number;
  eta?: number;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface DownloadProgress {
  task_id: number;
  filename: string;
  progress: number;
  speed: number;
  eta: number;
}

export async function fetchDownloads(): Promise<DownloadTask[]> {
  const res = await fetch(`${API_BASE}/api/downloads/`);
  if (!res.ok) throw new Error("Failed to fetch downloads");
  return res.json();
}

export async function addUrls(urls: string[]): Promise<DownloadTask[]> {
  const res = await fetch(`${API_BASE}/api/downloads/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ urls }),
  });
  if (!res.ok) throw new Error("Failed to add URLs");
  return res.json();
}

export async function startQueue(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/downloads/start`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to start queue");
}

export async function pauseQueue(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/downloads/pause`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to pause queue");
}

export async function resumeQueue(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/downloads/resume`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to resume queue");
}

export async function cancelDownload(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/downloads/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to cancel download");
}

export function createWebSocket(): WebSocket {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001";
  return new WebSocket(`${wsUrl}/ws/downloads`);
}
