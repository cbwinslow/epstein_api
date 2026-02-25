import { Download, Brain, Database, Activity } from "lucide-react";

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Command Center</h1>
        <p className="text-slate-400">Epstein OSINT Intelligence Pipeline</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Downloads"
          description="Manage file ingestion"
          icon={Download}
          href="/ingest"
          color="blue"
        />
        <StatCard
          title="Processing"
          description="ETL queue monitor"
          icon={Activity}
          href="/process"
          color="amber"
        />
        <StatCard
          title="Analysis"
          description="Agent swarm & graph"
          icon={Brain}
          href="/analyze"
          color="emerald"
        />
        <StatCard
          title="Settings"
          description="Configuration"
          icon={Database}
          href="/settings"
          color="purple"
        />
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold">Quick Start</h2>
        <ol className="list-decimal space-y-2 pl-5 text-slate-400">
          <li>Go to <span className="text-emerald-400">Settings</span> to configure models and concurrency</li>
          <li>Navigate to <span className="text-emerald-400">Ingest</span> to add DOJ file URLs</li>
          <li>Start the download queue and wait for completion</li>
          <li>Monitor processing in <span className="text-emerald-400">Processing Queue</span></li>
          <li>Run the agent swarm in <span className="text-emerald-400">Analysis</span></li>
        </ol>
      </div>
    </div>
  );
}

function StatCard({
  title,
  description,
  icon: Icon,
  href,
  color,
}: {
  title: string;
  description: string;
  icon: React.ElementType;
  href: string;
  color: "blue" | "amber" | "emerald" | "purple";
}) {
  const colors = {
    blue: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    amber: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    purple: "text-purple-400 bg-purple-500/10 border-purple-500/20",
  };

  return (
    <a
      href={href}
      className={`group block rounded-lg border p-4 transition-all hover:scale-[1.02] ${colors[color]}`}
    >
      <div className="flex items-center gap-3">
        <Icon className="h-5 w-5" />
        <div>
          <p className="font-medium">{title}</p>
          <p className="text-xs opacity-70">{description}</p>
        </div>
      </div>
    </a>
  );
}
