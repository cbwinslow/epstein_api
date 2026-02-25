"use client";

import { useCallback, useState, useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import { X, Loader2 } from "lucide-react";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

interface GraphNode {
  id: number;
  label: string;
  name: string;
}

interface GraphLink {
  source: number;
  target: number;
  type: string;
  depth_score: number;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface NodeDetails {
  n: Record<string, unknown>;
  outgoing?: Array<{
    target: string;
    type: string;
    score: number;
    evidence: string[];
  }>;
  incoming?: Array<{
    target: string;
    type: string;
    score: number;
    evidence: string[];
  }>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ENTITY_COLORS: Record<string, string> = {
  Person: "#ef4444",
  Organization: "#3b82f6",
  Location: "#22c55e",
  Aircraft: "#eab308",
  Event: "#a855f7",
};

export default function GraphExplorer() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [nodeDetails, setNodeDetails] = useState<NodeDetails | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/graph/network?limit=500&min_score=1`)
      .then((res) => res.json())
      .then((graphData) => {
        setData(graphData);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load graph:", err);
        setLoading(false);
      });
  }, []);

  const handleNodeClick = useCallback(async (node: any) => {
    const name = node.name || node.id;
    setSelectedNode(name);
    setDetailsLoading(true);
    setNodeDetails(null);

    try {
      const res = await fetch(`${API_BASE}/api/graph/node/${encodeURIComponent(name)}`);
      if (res.ok) {
        const details = await res.json();
        setNodeDetails(details);
      }
    } catch (err) {
      console.error("Failed to load node details:", err);
    } finally {
      setDetailsLoading(false);
    }
  }, []);

  const getNodeColor = (label: string) => {
    return ENTITY_COLORS[label] || "#6b7280";
  };

  const getLinkWidth = (score: number) => {
    return Math.max(1, score * 0.8);
  };

  const getLinkOpacity = (score: number) => {
    return Math.max(0.2, score / 10);
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg bg-slate-800/50 text-slate-400">
        No graph data available. Run the agent swarm to generate connections.
      </div>
    );
  }

  return (
    <div className="relative">
      <div ref={containerRef} className="h-[500px] w-full overflow-hidden rounded-lg bg-slate-900">
        <ForceGraph2D
          ref={graphRef}
          graphData={data}
          nodeLabel="name"
          nodeColor={(node: any) => getNodeColor(node.label)}
          nodeRelSize={6}
          linkWidth={(link: any) => getLinkWidth(link.depth_score)}
          linkColor={(link: any) => `rgba(148, 163, 184, ${getLinkOpacity(link.depth_score)})`}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          onNodeClick={handleNodeClick}
          backgroundColor="#0f172a"
          cooldownTicks={100}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
        />
      </div>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-4 text-xs">
        {Object.entries(ENTITY_COLORS).map(([label, color]) => (
          <div key={label} className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-slate-400">{label}</span>
          </div>
        ))}
      </div>

      {/* Depth Score Legend */}
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
        <span>Link thickness: Relationship depth (1-10)</span>
        <span>Thicker = Stronger connection</span>
      </div>

      {/* Detail Panel */}
      {selectedNode && (
        <div className="fixed right-4 top-20 z-50 w-80 rounded-lg border border-slate-700 bg-slate-900 p-4 shadow-xl">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-semibold text-emerald-400">{selectedNode}</h3>
            <button
              onClick={() => {
                setSelectedNode(null);
                setNodeDetails(null);
              }}
              className="rounded p-1 hover:bg-slate-800"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {detailsLoading ? (
            <div className="flex justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </div>
          ) : nodeDetails ? (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-slate-500">Type</p>
                <p className="text-sm">{(nodeDetails.n as any).labels?.[0] || "Unknown"}</p>
              </div>

              {nodeDetails.outgoing && nodeDetails.outgoing.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500">Connections ({nodeDetails.outgoing.length})</p>
                  <div className="mt-2 max-h-48 space-y-2 overflow-auto">
                    {nodeDetails.outgoing.map((rel, i) => (
                      <div key={i} className="rounded bg-slate-800 p-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{rel.target}</span>
                          <span
                            className="rounded px-2 py-0.5 text-xs"
                            style={{
                              backgroundColor: `rgba(34, 197, 94, ${rel.score / 10})`,
                            }}
                          >
                            {rel.score}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400">{rel.type}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-400">No details available</p>
          )}
        </div>
      )}
    </div>
  );
}
