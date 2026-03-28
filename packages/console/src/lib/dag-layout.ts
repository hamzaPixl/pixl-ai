/**
 * Shared DAG layout engine for workflow visualization.
 *
 * Extracted from the workflows page so both the workflow detail and
 * session detail pages can render the same DAG.
 */

import type { WorkflowDetail, WorkflowNodeDetail, WorkflowLoopDetail } from '@/types/api';

/* ------------------------------------------------------------------ */
/*  Node type colors                                                   */
/* ------------------------------------------------------------------ */

export type NodeType = 'task' | 'gate' | 'hook' | 'parallel' | 'merge' | 'sub_workflow';

export const NODE_STYLE: Record<NodeType, {
  fill: string;
  stroke: string;
  label: string;
}> = {
  task: { fill: '#3b82f6', stroke: '#2563eb', label: 'Task' },
  gate: { fill: '#f59e0b', stroke: '#d97706', label: 'Gate' },
  hook: { fill: '#6b7280', stroke: '#4b5563', label: 'Hook' },
  parallel: { fill: '#8b5cf6', stroke: '#7c3aed', label: 'Parallel' },
  merge: { fill: '#8b5cf6', stroke: '#7c3aed', label: 'Merge' },
  sub_workflow: { fill: '#10b981', stroke: '#059669', label: 'Sub-Workflow' },
};

export const NODE_TYPES: NodeType[] = ['task', 'gate', 'hook', 'parallel', 'merge', 'sub_workflow'];

/* ------------------------------------------------------------------ */
/*  DAG layout types                                                   */
/* ------------------------------------------------------------------ */

export interface LayoutNode {
  id: string;
  node: WorkflowNodeDetail;
  layer: number;
  indexInLayer: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface LayoutEdge {
  from: string;
  to: string;
  on: string;
  condition: string | null;
  isBack: boolean;
  path: string;
}

export interface LayoutLoop {
  loop: WorkflowLoopDetail;
  path: string;
}

export interface LayoutResult {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  loops: LayoutLoop[];
  width: number;
  height: number;
}

/* ------------------------------------------------------------------ */
/*  Layout constants                                                   */
/* ------------------------------------------------------------------ */

export const NODE_W = 200;
export const NODE_H = 52;
export const GAP_X = 24;
export const GAP_Y = 48;
export const PAD_X = 60;
export const PAD_Y = 30;

/* ------------------------------------------------------------------ */
/*  DAG layout engine — top-to-bottom, intrinsic height                */
/* ------------------------------------------------------------------ */

export function computeWorkflowDAG(
  workflow: WorkflowDetail,
  containerWidth: number,
): LayoutResult {
  const wfNodes = workflow.nodes ?? {};
  const edgesMap = workflow.edges ?? {};
  const loopsList = workflow.loops ?? [];

  const nodeIds = Object.keys(wfNodes);
  if (nodeIds.length === 0) return { nodes: [], edges: [], loops: [], width: 0, height: 0 };

  const forwardAdj: Record<string, string[]> = {};
  const inDegree: Record<string, number> = {};
  for (const nid of nodeIds) {
    forwardAdj[nid] = [];
    inDegree[nid] = 0;
  }
  for (const [fromId, edgeList] of Object.entries(edgesMap)) {
    if (!Array.isArray(edgeList)) continue;
    for (const e of edgeList) {
      if (e.on === 'success' && wfNodes[e.to]) {
        forwardAdj[fromId]?.push(e.to);
        inDegree[e.to] = (inDegree[e.to] ?? 0) + 1;
      }
    }
  }

  // Topological sort to assign layers (rows)
  const layerOf: Record<string, number> = {};
  const queue: string[] = [];
  for (const nid of nodeIds) {
    if ((inDegree[nid] ?? 0) === 0) queue.push(nid);
  }
  while (queue.length > 0) {
    const nid = queue.shift()!;
    if (layerOf[nid] === undefined) layerOf[nid] = 0;
    for (const next of (forwardAdj[nid] ?? [])) {
      layerOf[next] = Math.max(layerOf[next] ?? 0, layerOf[nid] + 1);
      inDegree[next]--;
      if (inDegree[next] === 0) queue.push(next);
    }
  }
  for (const nid of nodeIds) {
    if (layerOf[nid] === undefined) layerOf[nid] = 0;
  }

  // Group by layer
  const layers: Record<number, string[]> = {};
  let maxLayer = 0;
  for (const [nid, layer] of Object.entries(layerOf)) {
    if (!layers[layer]) layers[layer] = [];
    layers[layer].push(nid);
    maxLayer = Math.max(maxLayer, layer);
  }

  // Layout: top-to-bottom, centered horizontally
  const layoutNodes: LayoutNode[] = [];
  const nodeMap: Record<string, LayoutNode> = {};
  let svgWidth = containerWidth;

  for (let l = 0; l <= maxLayer; l++) {
    const layerNodes = layers[l] ?? [];
    const count = layerNodes.length;
    const rowW = count * NODE_W + (count - 1) * GAP_X;
    svgWidth = Math.max(svgWidth, rowW + PAD_X * 2);
    const startX = (svgWidth - rowW) / 2;

    for (let i = 0; i < layerNodes.length; i++) {
      const nid = layerNodes[i];
      if (!wfNodes[nid]) continue;
      const ln: LayoutNode = {
        id: nid,
        node: wfNodes[nid],
        layer: l,
        indexInLayer: i,
        x: startX + i * (NODE_W + GAP_X),
        y: PAD_Y + l * (NODE_H + GAP_Y),
        w: NODE_W,
        h: NODE_H,
      };
      layoutNodes.push(ln);
      nodeMap[nid] = ln;
    }
  }

  const svgHeight = PAD_Y * 2 + (maxLayer + 1) * NODE_H + maxLayer * GAP_Y;

  // Edges
  const loopFromTo = new Set(loopsList.map((lp) => `${lp.from_node}->${lp.to_node}`));
  const layoutEdges: LayoutEdge[] = [];

  for (const [fromId, edgeList] of Object.entries(edgesMap)) {
    if (!Array.isArray(edgeList)) continue;
    const src = nodeMap[fromId];
    if (!src) continue;
    for (const e of edgeList) {
      const dst = nodeMap[e.to];
      if (!dst) continue;
      const isBack = dst.layer <= src.layer || loopFromTo.has(`${fromId}->${e.to}`);
      let path: string;

      if (!isBack) {
        // Forward: bottom of source -> top of target
        const sx = src.x + src.w / 2;
        const sy = src.y + src.h;
        const tx = dst.x + dst.w / 2;
        const ty = dst.y;
        const dy = Math.abs(ty - sy) * 0.4;
        path = `M${sx},${sy} C${sx},${sy + dy} ${tx},${ty - dy} ${tx},${ty}`;
      } else {
        // Back-edge: curve to the right of nodes
        const sx = src.x + src.w;
        const sy = src.y + src.h / 2;
        const tx = dst.x + dst.w;
        const ty = dst.y + dst.h / 2;
        const bulge = Math.max(sx, tx) + 40 + Math.abs(sy - ty) * 0.08;
        path = `M${sx},${sy} C${bulge},${sy} ${bulge},${ty} ${tx},${ty}`;
      }
      layoutEdges.push({ from: fromId, to: e.to, on: e.on, condition: e.condition, isBack, path });
    }
  }

  // Loop back-edges
  const layoutLoops: LayoutLoop[] = [];
  for (const lp of loopsList) {
    const src = nodeMap[lp.from_node];
    const dst = nodeMap[lp.to_node];
    if (!src || !dst) continue;
    const alreadyEdge = layoutEdges.some((le) => le.from === lp.from_node && le.to === lp.to_node);
    if (alreadyEdge) {
      layoutLoops.push({ loop: lp, path: '' });
      continue;
    }
    const sx = src.x + src.w;
    const sy = src.y + src.h / 2;
    const tx = dst.x + dst.w;
    const ty = dst.y + dst.h / 2;
    const bulge = Math.max(sx, tx) + 50 + Math.abs(sy - ty) * 0.06;
    const path = `M${sx},${sy} C${bulge},${sy} ${bulge},${ty} ${tx},${ty}`;
    layoutLoops.push({ loop: lp, path });
  }

  return { nodes: layoutNodes, edges: layoutEdges, loops: layoutLoops, width: svgWidth, height: svgHeight };
}

/* ------------------------------------------------------------------ */
/*  Node label helpers                                                 */
/* ------------------------------------------------------------------ */

export function getNodeLabel(node: WorkflowNodeDetail | undefined): string {
  if (!node) return '';
  if (node.type === 'task' && node.task_config) {
    return node.task_config.agent ?? '';
  }
  if (node.type === 'gate' && node.gate_config) {
    return node.gate_config.name || node.gate_config.id || '';
  }
  if (node.type === 'hook' && node.hook_config) {
    const cfg = node.hook_config as Record<string, unknown>;
    return String(cfg.hook ?? cfg.hook_id ?? '');
  }
  if (node.type === 'sub_workflow' && node.metadata?.sub_workflow) {
    return node.metadata.sub_workflow;
  }
  return node.type ?? '';
}
