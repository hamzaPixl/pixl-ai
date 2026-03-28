/**
 * SVG-based directed graph visualization of agent workflow connections.
 * Nodes are positioned in columns by role, edges follow WORKFLOW_EDGES.
 */

import { useRef, useMemo, useCallback } from "react";
import type { AgentInfo } from "@/types/api";
import {
  type RoleKey,
  ROLE_META,
  ROLE_ORDER,
  WORKFLOW_EDGES,
  deriveRole,
} from "@/lib/agent-utils";

interface AgentGraphProps {
  agents: AgentInfo[];
  selectedAgent: string | null;
  onSelect: (agentName: string) => void;
}

const NODE_W = 130;
const NODE_H = 36;
const COL_GAP = 170;
const ROW_GAP = 54;
const PAD_X = 40;
const PAD_Y = 40;

type NodePos = { x: number; y: number; role: RoleKey; agent: AgentInfo };

export function AgentGraph({ agents, selectedAgent, onSelect }: AgentGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  const { nodes, width, height } = useMemo(() => {
    // Group agents by role
    const grouped: Record<RoleKey, AgentInfo[]> = {
      strategy: [],
      implementation: [],
      testing: [],
      review: [],
      operations: [],
    };
    for (const a of agents) grouped[deriveRole(a)].push(a);
    for (const k of ROLE_ORDER) grouped[k].sort((a, b) => a.name.localeCompare(b.name));

    const nodeMap = new Map<string, NodePos>();
    let maxRows = 0;

    for (let col = 0; col < ROLE_ORDER.length; col++) {
      const role = ROLE_ORDER[col];
      const list = grouped[role];
      maxRows = Math.max(maxRows, list.length);
      for (let row = 0; row < list.length; row++) {
        nodeMap.set(list[row].name, {
          x: PAD_X + col * COL_GAP,
          y: PAD_Y + row * ROW_GAP,
          role,
          agent: list[row],
        });
      }
    }

    return {
      nodes: nodeMap,
      width: PAD_X * 2 + (ROLE_ORDER.length - 1) * COL_GAP + NODE_W,
      height: PAD_Y * 2 + Math.max(0, maxRows - 1) * ROW_GAP + NODE_H,
    };
  }, [agents]);

  // Detect bidirectional edges for curve rendering
  const biEdges = useMemo(() => {
    const set = new Set<string>();
    for (const [s, t] of WORKFLOW_EDGES) {
      if (WORKFLOW_EDGES.some(([rs, rt]) => rs === t && rt === s)) {
        set.add(`${s}->${t}`);
      }
    }
    return set;
  }, []);

  const handleClick = useCallback(
    (name: string) => (e: React.MouseEvent) => {
      e.stopPropagation();
      onSelect(name);
    },
    [onSelect],
  );

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-full"
      style={{ minHeight: 300 }}
    >
      <defs>
        <marker
          id="arrow"
          viewBox="0 0 10 7"
          refX="10"
          refY="3.5"
          markerWidth="8"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="currentColor" className="text-muted-foreground/50" />
        </marker>
        <marker
          id="arrow-highlight"
          viewBox="0 0 10 7"
          refX="10"
          refY="3.5"
          markerWidth="8"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="currentColor" className="text-foreground" />
        </marker>
      </defs>

      {/* Column labels */}
      {ROLE_ORDER.map((role, col) => (
        <text
          key={role}
          x={PAD_X + col * COL_GAP + NODE_W / 2}
          y={PAD_Y - 16}
          textAnchor="middle"
          className="fill-muted-foreground text-[10px] uppercase"
          style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.05em" }}
        >
          {ROLE_META[role].label}
        </text>
      ))}

      {/* Edges */}
      {WORKFLOW_EDGES.map(([s, t]) => {
        const src = nodes.get(s);
        const tgt = nodes.get(t);
        if (!src || !tgt) return null;

        const isBi = biEdges.has(`${s}->${t}`);
        const isConnected =
          selectedAgent === s || selectedAgent === t;
        const dimmed = selectedAgent && !isConnected;

        const sx = src.x + NODE_W;
        const sy = src.y + NODE_H / 2;
        const tx = tgt.x;
        const ty = tgt.y + NODE_H / 2;

        // For reverse edges (target col <= source col) or bidirectional, use curves
        const isReverse = tgt.x <= src.x;
        const curveOffset = isBi ? 12 : 0;

        let d: string;
        if (isReverse) {
          // Route below/above with a curve
          const midY = Math.max(sy, ty) + 40;
          d = `M${sx},${sy} C${sx + 30},${sy} ${sx + 30},${midY} ${(sx + tx) / 2},${midY} C${tx - 30},${midY} ${tx - 30},${ty} ${tx},${ty}`;
        } else {
          const mx = (sx + tx) / 2;
          d = `M${sx},${sy + curveOffset} C${mx},${sy + curveOffset} ${mx},${ty + curveOffset} ${tx},${ty + curveOffset}`;
        }

        return (
          <path
            key={`${s}->${t}`}
            d={d}
            fill="none"
            stroke="currentColor"
            strokeWidth={isConnected ? 1.5 : 1}
            className={
              dimmed
                ? "text-muted-foreground/15"
                : isConnected
                  ? "text-foreground/60"
                  : "text-muted-foreground/30"
            }
            markerEnd={isConnected ? "url(#arrow-highlight)" : "url(#arrow)"}
            style={{ transition: "all 0.2s" }}
          />
        );
      })}

      {/* Nodes */}
      {Array.from(nodes.entries()).map(([name, node]) => {
        const meta = ROLE_META[node.role];
        const isSelected = selectedAgent === name;
        const isConnected =
          selectedAgent &&
          !isSelected &&
          WORKFLOW_EDGES.some(
            ([s, t]) =>
              (s === selectedAgent && t === name) ||
              (t === selectedAgent && s === name),
          );
        const dimmed = selectedAgent && !isSelected && !isConnected;

        return (
          <g
            key={name}
            onClick={handleClick(name)}
            style={{ cursor: "pointer", transition: "opacity 0.2s" }}
            opacity={dimmed ? 0.3 : 1}
          >
            <rect
              x={node.x}
              y={node.y}
              width={NODE_W}
              height={NODE_H}
              rx={8}
              fill={isSelected ? meta.fill : "currentColor"}
              className={isSelected ? "" : "text-card"}
              stroke={meta.fill}
              strokeWidth={isSelected ? 2 : 1.5}
              style={{ transition: "all 0.2s" }}
            />
            <text
              x={node.x + NODE_W / 2}
              y={node.y + NODE_H / 2 + 1}
              textAnchor="middle"
              dominantBaseline="central"
              fill={isSelected ? "white" : meta.fill}
              style={{ fontSize: 11, fontWeight: 500, pointerEvents: "none" }}
            >
              {name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
