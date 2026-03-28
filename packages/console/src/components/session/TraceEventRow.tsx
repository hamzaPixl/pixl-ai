/**
 * TraceEventRow — Compact single-line event with expandable detail.
 *
 * Renders all TraceEventNode kinds: tool, thinking, text, error,
 * query, gate, recovery, contract. Linear-style compact row by default,
 * click to expand into full detail.
 */

import { useState } from 'react';
import {
  Brain,
  MessageSquare,
  AlertTriangle,
  Zap,
  Shield,
  RefreshCw,
  FileCheck,
  ChevronDown,
  ChevronRight,
  Loader2,
  Clock,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn, formatModelName, getModelBadgeColor, formatTokenCount, estimateTokenCost } from '@/lib/utils';
import type { TraceEventNode } from '@/lib/session-utils';

const THINKING_PREVIEW_LEN = 120;
const TEXT_PREVIEW_LEN = 200;

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

// Lifecycle status dot
function LifecycleDot({ lifecycle }: { lifecycle?: string }) {
  if (lifecycle === 'running' || lifecycle === 'started') {
    return <Loader2 className="h-3 w-3 text-amber-500 animate-spin flex-shrink-0" />;
  }
  if (lifecycle === 'failed') {
    return <span className="h-2 w-2 rounded-full bg-red-500 flex-shrink-0" />;
  }
  if (lifecycle === 'completed') {
    return <span className="h-2 w-2 rounded-full bg-green-500 flex-shrink-0" />;
  }
  return <span className="h-2 w-2 rounded-full bg-muted-foreground/40 flex-shrink-0" />;
}

export function TraceEventRow({ event }: { event: TraceEventNode }) {
  const [expanded, setExpanded] = useState(false);
  const time = formatTime(event.timestamp);

  switch (event.kind) {
    case 'tool':
      // Tools are rendered by ToolCallExpansion in TaskTraceBlock
      return null;

    case 'thinking':
      return <ThinkingRow event={event} time={time} expanded={expanded} setExpanded={setExpanded} />;

    case 'text':
      return <TextRow event={event} time={time} expanded={expanded} setExpanded={setExpanded} />;

    case 'error':
      return <ErrorRow event={event} time={time} />;

    case 'query':
      return <QueryRow event={event} time={time} expanded={expanded} setExpanded={setExpanded} />;

    case 'gate':
      return <GateRow event={event} time={time} expanded={expanded} setExpanded={setExpanded} />;

    case 'recovery':
      return <RecoveryRow event={event} time={time} expanded={expanded} setExpanded={setExpanded} />;

    case 'contract':
      return <ContractRow event={event} time={time} />;
  }
}

// Thinking Row

function ThinkingRow({
  event,
  time,
  expanded,
  setExpanded,
}: {
  event: Extract<TraceEventNode, { kind: 'thinking' }>;
  time: string;
  expanded: boolean;
  setExpanded: (v: boolean) => void;
}) {
  const text = event.text;
  const isLong = text && text.length > THINKING_PREVIEW_LEN;

  return (
    <div className={cn(
      "flex items-start gap-2 text-xs",
      event.lifecycle === 'running' && "animate-pulse"
    )}>
      <span className="text-muted-foreground font-mono w-16 flex-shrink-0 tabular-nums">{time}</span>
      <Brain className="h-3 w-3 text-purple-500 flex-shrink-0 mt-0.5" />
      <Badge variant="outline" className="text-[9px] px-1 h-4 text-purple-500 border-purple-500/30">think</Badge>
      <button
        className="flex-1 min-w-0 text-muted-foreground italic text-left truncate"
        onClick={() => isLong && setExpanded(!expanded)}
      >
        {isLong && (expanded ? <ChevronDown className="h-2.5 w-2.5 inline mr-1" /> : <ChevronRight className="h-2.5 w-2.5 inline mr-1" />)}
        {expanded ? text : text?.slice(0, THINKING_PREVIEW_LEN)}{!expanded && isLong ? '...' : ''}
      </button>
      <LifecycleDot lifecycle={event.lifecycle} />
    </div>
  );
}

// Text Row

function TextRow({
  event,
  time,
  expanded,
  setExpanded,
}: {
  event: Extract<TraceEventNode, { kind: 'text' }>;
  time: string;
  expanded: boolean;
  setExpanded: (v: boolean) => void;
}) {
  const text = event.text;
  const isLong = text && text.length > TEXT_PREVIEW_LEN;

  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="text-muted-foreground font-mono w-16 flex-shrink-0 tabular-nums">{time}</span>
      <MessageSquare className="h-3 w-3 text-blue-500 flex-shrink-0 mt-0.5" />
      <Badge variant="outline" className="text-[9px] px-1 h-4 text-blue-500 border-blue-500/30">text</Badge>
      <button
        className="flex-1 min-w-0 text-muted-foreground text-left break-words"
        onClick={() => isLong && setExpanded(!expanded)}
      >
        {isLong && (expanded ? <ChevronDown className="h-2.5 w-2.5 inline mr-1" /> : <ChevronRight className="h-2.5 w-2.5 inline mr-1" />)}
        {expanded ? text : text?.slice(0, TEXT_PREVIEW_LEN)}{!expanded && isLong ? '...' : ''}
      </button>
    </div>
  );
}

// Error Row

function ErrorRow({
  event,
  time,
}: {
  event: Extract<TraceEventNode, { kind: 'error' }>;
  time: string;
}) {
  return (
    <div className="flex items-start gap-2 text-xs border-l-2 border-red-500/30 pl-1">
      <span className="text-muted-foreground font-mono w-16 flex-shrink-0 tabular-nums">{time}</span>
      <AlertTriangle className="h-3 w-3 text-red-500 flex-shrink-0 mt-0.5" />
      <Badge variant="outline" className="text-[9px] px-1 h-4 text-red-500 border-red-500/30">error</Badge>
      <span className="flex-1 min-w-0 text-red-500 break-words">
        {event.errorType && <span className="font-medium">{event.errorType}: </span>}
        {event.error}
      </span>
      <LifecycleDot lifecycle="failed" />
    </div>
  );
}

// Query Row

function QueryRow({
  event,
  time,
  expanded,
  setExpanded,
}: {
  event: Extract<TraceEventNode, { kind: 'query' }>;
  time: string;
  expanded: boolean;
  setExpanded: (v: boolean) => void;
}) {
  return (
    <div className={cn(
      "text-xs",
      event.lifecycle === 'running' && "animate-pulse"
    )}>
      <button
        className="flex items-center gap-2 w-full text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-muted-foreground font-mono w-16 flex-shrink-0 tabular-nums">{time}</span>
        <Zap className="h-3 w-3 text-yellow-500 flex-shrink-0" />
        <Badge variant="outline" className="text-[9px] px-1 h-4 text-yellow-600 border-yellow-500/30">query</Badge>
        {event.model && (
          <span className={cn("inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-medium", getModelBadgeColor(event.model))}>
            {formatModelName(event.model)}
          </span>
        )}
        {event.totalTokens !== undefined && (
          <span className="text-muted-foreground tabular-nums">{formatTokenCount(event.totalTokens)} tok</span>
        )}
        {event.totalTokens !== undefined && event.model && (
          <span className="text-muted-foreground/60 tabular-nums">{estimateTokenCost(event.model, event.totalTokens)}</span>
        )}
        {event.durationSeconds !== undefined && (
          <span className="text-muted-foreground tabular-nums ml-auto">{event.durationSeconds.toFixed(1)}s</span>
        )}
        <LifecycleDot lifecycle={event.lifecycle} />
      </button>
      {expanded && (
        <div className="ml-20 mt-1 p-2 rounded bg-muted/30 border space-y-1">
          {event.numTurns !== undefined && (
            <div className="text-muted-foreground"><span className="font-medium">Turns:</span> {event.numTurns}</div>
          )}
          {event.promptPreview && (
            <div>
              <span className="font-medium text-muted-foreground">Prompt:</span>
              <pre className="mt-1 text-[10px] font-mono text-muted-foreground whitespace-pre-wrap max-h-32 overflow-y-auto">{event.promptPreview}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Gate Row

const GATE_CONFIG = {
  requested: { icon: <Shield className="h-3 w-3 text-amber-500" />, color: 'text-amber-500', border: 'border-amber-500/30' },
  approved: { icon: <ShieldCheck className="h-3 w-3 text-green-500" />, color: 'text-green-500', border: 'border-green-500/30' },
  rejected: { icon: <ShieldAlert className="h-3 w-3 text-red-500" />, color: 'text-red-500', border: 'border-red-500/30' },
  timeout: { icon: <Clock className="h-3 w-3 text-muted-foreground" />, color: 'text-muted-foreground', border: 'border-muted-foreground/30' },
};

function GateRow({
  event,
  time,
  expanded,
  setExpanded,
}: {
  event: Extract<TraceEventNode, { kind: 'gate' }>;
  time: string;
  expanded: boolean;
  setExpanded: (v: boolean) => void;
}) {
  const cfg = GATE_CONFIG[event.gateAction];
  return (
    <div className="text-xs">
      <button
        className="flex items-center gap-2 w-full text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-muted-foreground font-mono w-16 flex-shrink-0 tabular-nums">{time}</span>
        {cfg.icon}
        <Badge variant="outline" className={cn("text-[9px] px-1 h-4", cfg.color, cfg.border)}>gate</Badge>
        <span className={cn("font-medium", cfg.color)}>{event.gateAction}</span>
        {event.approver && <span className="text-muted-foreground">by {event.approver}</span>}
        {event.gateAction === 'requested' && <LifecycleDot lifecycle="running" />}
        {event.gateAction === 'approved' && <LifecycleDot lifecycle="completed" />}
        {(event.gateAction === 'rejected' || event.gateAction === 'timeout') && <LifecycleDot lifecycle="failed" />}
      </button>
      {expanded && (
        <div className="ml-20 mt-1 p-2 rounded bg-muted/30 border space-y-1 text-muted-foreground">
          {event.reason && <div><span className="font-medium">Reason:</span> {event.reason}</div>}
          {event.artifacts && event.artifacts.length > 0 && (
            <div><span className="font-medium">Artifacts:</span> {event.artifacts.join(', ')}</div>
          )}
        </div>
      )}
    </div>
  );
}

// Recovery Row

const RECOVERY_CONFIG = {
  requested: { color: 'text-orange-500' },
  decision: { color: 'text-amber-500' },
  succeeded: { color: 'text-green-500' },
  failed: { color: 'text-red-500' },
  escalated: { color: 'text-red-600' },
};

function RecoveryRow({
  event,
  time,
  expanded,
  setExpanded,
}: {
  event: Extract<TraceEventNode, { kind: 'recovery' }>;
  time: string;
  expanded: boolean;
  setExpanded: (v: boolean) => void;
}) {
  const cfg = RECOVERY_CONFIG[event.recoveryAction];
  return (
    <div className="text-xs">
      <button
        className="flex items-center gap-2 w-full text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-muted-foreground font-mono w-16 flex-shrink-0 tabular-nums">{time}</span>
        <RefreshCw className={cn("h-3 w-3", cfg.color)} />
        <Badge variant="outline" className={cn("text-[9px] px-1 h-4", cfg.color)}>recovery</Badge>
        <span className={cn("font-medium", cfg.color)}>{event.recoveryAction}</span>
        {event.action && <span className="text-muted-foreground">{event.action}</span>}
        {event.attempt !== undefined && <span className="text-muted-foreground tabular-nums">attempt {event.attempt}</span>}
        {event.recoveryAction === 'succeeded' && <LifecycleDot lifecycle="completed" />}
        {event.recoveryAction === 'failed' && <LifecycleDot lifecycle="failed" />}
        {(event.recoveryAction === 'requested' || event.recoveryAction === 'decision') && <LifecycleDot lifecycle="running" />}
      </button>
      {expanded && (
        <div className="ml-20 mt-1 p-2 rounded bg-muted/30 border space-y-1 text-muted-foreground">
          {event.errorType && <div><span className="font-medium">Error type:</span> {event.errorType}</div>}
          {event.decisionReason && <div><span className="font-medium">Decision:</span> {event.decisionReason}</div>}
        </div>
      )}
    </div>
  );
}

// Contract Row

function ContractRow({
  event,
  time,
}: {
  event: Extract<TraceEventNode, { kind: 'contract' }>;
  time: string;
}) {
  const isPassed = event.contractAction === 'passed';
  const isViolation = event.contractAction === 'violation';

  return (
    <div className={cn(
      "flex items-start gap-2 text-xs",
      isViolation && "border-l-2 border-red-500/30 pl-1"
    )}>
      <span className="text-muted-foreground font-mono w-16 flex-shrink-0 tabular-nums">{time}</span>
      <FileCheck className={cn("h-3 w-3 flex-shrink-0 mt-0.5", isPassed ? "text-green-500" : isViolation ? "text-red-500" : "text-amber-500")} />
      <Badge variant="outline" className={cn(
        "text-[9px] px-1 h-4",
        isPassed ? "text-green-500 border-green-500/30" : isViolation ? "text-red-500 border-red-500/30" : "text-amber-500 border-amber-500/30"
      )}>contract</Badge>
      <span className={cn(
        "font-medium",
        isPassed ? "text-green-500" : isViolation ? "text-red-500" : "text-amber-500"
      )}>
        {event.contractAction}
      </span>
      {event.check && <span className="text-muted-foreground">{event.check}</span>}
      {event.warning && <span className="text-muted-foreground">{event.warning}</span>}
      {event.violations && event.violations.length > 0 && (
        <span className="text-red-500 truncate">{event.violations.join('; ')}</span>
      )}
      <LifecycleDot lifecycle={isPassed ? 'completed' : isViolation ? 'failed' : undefined} />
    </div>
  );
}
