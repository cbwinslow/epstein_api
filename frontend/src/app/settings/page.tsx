"use client";

import { useState, useEffect, useCallback } from "react";
import { Settings, Save, Loader2 } from "lucide-react";

interface AvailableModel {
  id: string;
  name: string;
  context_length: number | null;
}

interface SettingsConfig {
  openrouter: {
    api_key: string;
    model_simple: string;
    model_complex: string;
    model_vision: string;
    model_high_context: string;
  };
  ollama: {
    base_url: string;
    model: string;
  };
  downloader: {
    max_concurrent: number;
  };
  celery: {
    worker_concurrency: number;
  };
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAvailableModels(): Promise<AvailableModel[]> {
  const res = await fetch(`${API_BASE}/api/models/available`);
  if (!res.ok) throw new Error("Failed to fetch models");
  return res.json();
}

async function fetchConfig(): Promise<SettingsConfig> {
  const res = await fetch(`${API_BASE}/api/config`);
  if (!res.ok) throw new Error("Failed to fetch config");
  return res.json();
}

async function saveConfig(config: SettingsConfig): Promise<void> {
  const res = await fetch(`${API_BASE}/api/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error("Failed to save config");
}

export default function SettingsPage() {
  const [models, setModels] = useState<AvailableModel[]>([]);
  const [config, setConfig] = useState<SettingsConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [modelsData, configData] = await Promise.all([
        fetchAvailableModels(),
        fetchConfig(),
      ]);
      setModels(modelsData);
      setConfig(configData);
    } catch (err) {
      console.error("Failed to load settings:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setSaved(false);
    try {
      await saveConfig(config);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save:", err);
    } finally {
      setSaving(false);
    }
  };

  const updateConfig = (path: string, value: unknown) => {
    if (!config) return;
    setConfig((prev) => {
      if (!prev) return prev;
      const keys = path.split(".");
      const newConfig = { ...prev };
      let current: Record<string, unknown> = newConfig as unknown as Record<string, unknown>;
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = { ...(current[keys[i]] as Record<string, unknown>) };
        current = current[keys[i]] as Record<string, unknown>;
      }
      current[keys[keys.length - 1]] = value;
      return newConfig;
    });
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
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-slate-400">Configure models and concurrency limits</p>
      </div>

      {/* Model Selection */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="mb-4 flex items-center gap-2 font-semibold">
          <Settings className="h-5 w-5" />
          Model Selection
        </h2>

        <div className="space-y-4">
          {/* OpenRouter API Key */}
          <div>
            <label className="mb-1 block text-sm font-medium">OpenRouter API Key</label>
            <input
              type="password"
              value={config?.openrouter.api_key ?? ""}
              onChange={(e) => updateConfig("openrouter.api_key", e.target.value)}
              placeholder="sk-or-..."
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm"
            />
          </div>

          {/* Model Dropdowns */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Simple Tasks</label>
              <select
                value={config?.openrouter.model_simple ?? ""}
                onChange={(e) => updateConfig("openrouter.model_simple", e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm"
              >
                <option value="">Select model...</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.context_length ? `${m.context_length / 1000}k` : "?"})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">Complex Reasoning</label>
              <select
                value={config?.openrouter.model_complex ?? ""}
                onChange={(e) => updateConfig("openrouter.model_complex", e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm"
              >
                <option value="">Select model...</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.context_length ? `${m.context_length / 1000}k` : "?"})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">Vision</label>
              <select
                value={config?.openrouter.model_vision ?? ""}
                onChange={(e) => updateConfig("openrouter.model_vision", e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm"
              >
                <option value="">Select model...</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.context_length ? `${m.context_length / 1000}k` : "?"})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">High Context</label>
              <select
                value={config?.openrouter.model_high_context ?? ""}
                onChange={(e) => updateConfig("openrouter.model_high_context", e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm"
              >
                <option value="">Select model...</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.context_length ? `${m.context_length / 1000}k` : "?"})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Ollama */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Ollama Base URL</label>
              <input
                type="text"
                value={config?.ollama.base_url ?? ""}
                onChange={(e) => updateConfig("ollama.base_url", e.target.value)}
                placeholder="http://localhost:11434"
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Ollama Fallback Model</label>
              <input
                type="text"
                value={config?.ollama.model ?? ""}
                onChange={(e) => updateConfig("ollama.model", e.target.value)}
                placeholder="llama3.2:3b"
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Concurrency */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="mb-4 font-semibold">Concurrency Limits</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium">Max Concurrent Downloads</label>
            <input
              type="number"
              min={1}
              max={50}
              value={config?.downloader.max_concurrent ?? 5}
              onChange={(e) => updateConfig("downloader.max_concurrent", parseInt(e.target.value))}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Celery Worker Concurrency</label>
            <input
              type="number"
              min={1}
              max={32}
              value={config?.celery.worker_concurrency ?? 4}
              onChange={(e) => updateConfig("celery.worker_concurrency", parseInt(e.target.value))}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-6 py-2 font-medium hover:bg-emerald-700 disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {saving ? "Saving..." : saved ? "Saved!" : "Save Settings"}
        </button>
      </div>
    </div>
  );
}
