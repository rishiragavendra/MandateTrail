"use client";
import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Json } from "../lib/api";
export default function Provenance({
  graph,
  onSelect,
}: {
  graph: Json;
  onSelect: (data: Json) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    const cols: Record<string, number> = {
      source: 0,
      extraction: 1,
      persistent_storage: 2,
      session_retrieval: 3,
      payment: 4,
    };
    const rows: Record<number, number> = {};
    const nodes: Node[] = graph.nodes.map((n: Json) => {
      const col = cols[n.type] ?? 1;
      const row = rows[col] ?? 0;
      rows[col] = row + 1;
      return {
        id: n.id,
        position: { x: col * 260, y: row * 105 },
        data: {
          label: (
            <div>
              <small>{n.type.replaceAll("_", " ")}</small>
              <strong>{n.label}</strong>
              <small
                className={n.trust === "VERIFIED_REGISTRY" ? "good" : "muted"}
              >
                {n.trust}
              </small>
            </div>
          ),
        },
        style: {
          background: "#141D30",
          color: "#F8FAFC",
          border: `1px solid ${n.trust === "EXTERNAL_UNVERIFIED" ? "#a16207" : "#33496b"}`,
          width: 215,
          borderRadius: 10,
        },
      };
    });
    const edges: Edge[] = graph.edges.map((e: Json, i: number) => ({
      id: "edge-" + i,
      ...e,
      animated: true,
      style: { stroke: "#6366F1", strokeWidth: 1.4 },
    }));
    return { nodes, edges };
  }, [graph]);
  return (
    <div className="graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        minZoom={0.15}
        maxZoom={2}
        onNodeClick={(_, node) =>
          onSelect(graph.nodes.find((n: Json) => n.id === node.id))
        }
        colorMode="dark"
      >
        <Background color="#273449" gap={24} />
        <Controls />
        <MiniMap nodeColor="#6366F1" maskColor="#080d1bcc" />
      </ReactFlow>
    </div>
  );
}
