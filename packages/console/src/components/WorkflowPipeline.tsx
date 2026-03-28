/**
 * Vertical pipeline visualization replacing the SVG-based WorkflowDAG.
 *
 * Uses DOM elements (HTML/CSS/Tailwind + framer-motion) for a modern,
 * interactive pipeline view. Reuses computeWorkflowDAG() for topological
 * layer ordering but renders as vertical cards instead of SVG rects.
 */

import { useMemo, useEffect, useRef } from 'react';
import { computeWorkflowDAG } from '@/lib/dag-layout';
import type { NodeType } from '@/lib/dag-layout';
import type { WorkflowDetail, NodeInstance } from '@/types/api';
import { WorkflowPipelineNode } from './WorkflowPipelineNode';
import { WorkflowPipelineConnector } from './WorkflowPipelineConnector';
import type { ExecutionState, NodeExecutionState } from './WorkflowStatusIcon';

export type { ExecutionState, NodeExecutionState };

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

export interface WorkflowPipelineProps {
  workflow: WorkflowDetail;
  selectedNode: string | null;
  hoveredNode: string | null;
  onSelect: (nodeId: string) => void;
  onHover: (nodeId: string | null) => void;
  activeType: NodeType | null;
  /** Execution state overlay — when provided, nodes show live state */
  nodeStates?: Record<string, NodeExecutionState>;
  /** Node instance data for model/duration info */
  nodeInstances?: Record<string, NodeInstance>;
}

/* ------------------------------------------------------------------ */
/*  Layer grouping                                                     */
/* ------------------------------------------------------------------ */

interface LayerGroup {
  layer: number;
  nodeIds: string[];
}

function groupByLayer(workflow: WorkflowDetail): LayerGroup[] {
  // Use existing layout engine for topological ordering (ignore pixel positions)
  const layout = computeWorkflowDAG(workflow, 800);
  const layerMap = new Map<number, string[]>();

  for (const ln of layout.nodes) {
    const existing = layerMap.get(ln.layer);
    if (existing) {
      existing.push(ln.id);
    } else {
      layerMap.set(ln.layer, [ln.id]);
    }
  }

  return Array.from(layerMap.entries())
    .sort(([a], [b]) => a - b)
    .map(([layer, nodeIds]) => ({ layer, nodeIds }));
}

/* ------------------------------------------------------------------ */
/*  Loop indicator                                                     */
/* ------------------------------------------------------------------ */

function LoopIndicator({ toNode, maxIterations }: { toNode: string; maxIterations: number }) {
  return (
    <div className="flex items-center justify-center py-1">
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-dashed border-muted-foreground/30 bg-muted/30 text-[10px] text-muted-foreground">
        <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
          <path d="M3 3v5h5" />
          <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
          <path d="M16 16h5v5" />
        </svg>
        loops to {toNode} (max {maxIterations})
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function WorkflowPipeline({
  workflow,
  selectedNode,
  hoveredNode,
  onSelect,
  onHover,
  activeType,
  nodeStates,
  nodeInstances,
}: WorkflowPipelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const layers = useMemo(() => groupByLayer(workflow), [workflow]);
  const nodes = workflow.nodes ?? {};
  const loops = workflow.loops ?? [];
  const hasStates = nodeStates != null && Object.keys(nodeStates).length > 0;

  const loopsByFromNode = useMemo(() => {
    const map = new Map<string, typeof loops>();
    for (const lp of loops) {
      const existing = map.get(lp.from_node);
      if (existing) {
        existing.push(lp);
      } else {
        map.set(lp.from_node, [lp]);
      }
    }
    return map;
  }, [loops]);

  // Auto-scroll to running node
  useEffect(() => {
    if (!hasStates) return;
    const runningId = Object.entries(nodeStates ?? {}).find(([, s]) => s.state === 'running')?.[0];
    if (runningId) {
      const el = nodeRefs.current.get(runningId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [nodeStates, hasStates]);

  const firstSingleBeforeParallelIdx = useMemo(() => {
    return layers.findIndex((layer, idx) => {
      const next = layers[idx + 1];
      return layer.nodeIds.length === 1 && (next?.nodeIds.length ?? 0) > 1;
    });
  }, [layers]);

  return (
    <div ref={containerRef} className="w-full h-full overflow-y-auto p-4">
      <div className="max-w-lg mx-auto flex flex-col">
        {layers.map((layer, layerIdx) => {
          const isParallel = layer.nodeIds.length > 1;
          const prevLayer = layerIdx > 0 ? layers[layerIdx - 1] : null;
          const nextLayer = layerIdx < layers.length - 1 ? layers[layerIdx + 1] : null;
          const isBranching = nextLayer != null && nextLayer.nodeIds.length > 1;
          const isMerging = prevLayer != null && prevLayer.nodeIds.length > 1;

          // Determine source state for connector (use previous layer's first node state)
          const prevNodeIds = prevLayer?.nodeIds ?? [];
          const prevStates = prevNodeIds.map((id) => nodeStates?.[id]?.state).filter(Boolean) as ExecutionState[];
          const connectorSourceState = prevStates.length > 0
            ? (prevStates.includes('failed') ? 'failed' : prevStates.includes('running') ? 'running' : prevStates[0])
            : undefined;

          return (
            <div key={layer.layer}>
              {/* Connector before this layer (skip for first) */}
              {layerIdx > 0 && (
                <WorkflowPipelineConnector
                  sourceState={connectorSourceState}
                  isBranching={isBranching && layerIdx === firstSingleBeforeParallelIdx}
                  isMerging={isMerging && layer.nodeIds.length === 1}
                />
              )}

              {/* Branching indicator before parallel layer */}
              {isParallel && prevLayer && prevLayer.nodeIds.length === 1 && (
                <WorkflowPipelineConnector
                  sourceState={connectorSourceState}
                  isBranching
                />
              )}

              {/* Nodes in this layer */}
              {isParallel ? (
                <div className="flex gap-3">
                  {layer.nodeIds.map((nodeId) => {
                    const node = nodes[nodeId];
                    if (!node) return null;
                    return (
                      <div
                        key={nodeId}
                        ref={(el) => { if (el) nodeRefs.current.set(nodeId, el); }}
                        className="flex-1 min-w-0"
                      >
                        <WorkflowPipelineNode
                          nodeId={nodeId}
                          node={node}
                          executionState={nodeStates?.[nodeId]}
                          isSelected={selectedNode === nodeId}
                          isHovered={hoveredNode === nodeId}
                          activeType={activeType}
                          nodeInstance={nodeInstances?.[nodeId]}
                          hasExecutionStates={hasStates}
                          onSelect={onSelect}
                          onHover={onHover}
                        />
                      </div>
                    );
                  })}
                </div>
              ) : (
                layer.nodeIds.map((nodeId) => {
                  const node = nodes[nodeId];
                  if (!node) return null;
                  return (
                    <div
                      key={nodeId}
                      ref={(el) => { if (el) nodeRefs.current.set(nodeId, el); }}
                    >
                      <WorkflowPipelineNode
                        nodeId={nodeId}
                        node={node}
                        executionState={nodeStates?.[nodeId]}
                        isSelected={selectedNode === nodeId}
                        isHovered={hoveredNode === nodeId}
                        activeType={activeType}
                        nodeInstance={nodeInstances?.[nodeId]}
                        hasExecutionStates={hasStates}
                        onSelect={onSelect}
                        onHover={onHover}
                      />
                    </div>
                  );
                })
              )}

              {/* Merging indicator after parallel layer */}
              {isParallel && nextLayer && nextLayer.nodeIds.length === 1 && (
                <WorkflowPipelineConnector
                  sourceState={connectorSourceState}
                  isMerging
                />
              )}

              {/* Loop indicators for nodes in this layer */}
              {layer.nodeIds.map((nodeId) => {
                const nodeLoops = loopsByFromNode.get(nodeId);
                if (!nodeLoops) return null;
                return nodeLoops.map((lp) => (
                  <LoopIndicator
                    key={lp.id}
                    toNode={lp.to_node}
                    maxIterations={lp.max_iterations}
                  />
                ));
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
