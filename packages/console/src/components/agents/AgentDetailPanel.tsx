import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Separator } from "@/components/ui/separator";
import {
  RotateCcw,
  Loader2,
  X,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  ROLE_META,
  deriveRole,
  deriveTier,
  TIER_META,
  stripProvider,
  getAgentConnections,
} from "@/lib/agent-utils";
import type { AgentInfo } from "@/types/api";

export interface AgentDetailPanelProps {
  agent: AgentInfo;
  allowedModels: string[];
  onModelChange: (model: string) => void;
  onReset: () => void;
  isPending: boolean;
  onClose: () => void;
  allAgents: AgentInfo[];
}

export function AgentDetailPanel({
  agent,
  allowedModels,
  onModelChange,
  onReset,
  isPending,
  onClose,
  allAgents,
}: AgentDetailPanelProps) {
  const role = deriveRole(agent);
  const meta = ROLE_META[role];
  const tier = deriveTier(agent.effective_model);
  const tierMeta = TIER_META[tier];
  const connections = getAgentConnections(agent.name);

  return (
    <div className="h-full flex flex-col">
      {/* Panel header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full shrink-0 ${meta.dot}`}
          />
          <span className="font-semibold text-sm truncate">{agent.name}</span>
          <Badge
            variant="secondary"
            className="text-[10px] px-1.5 py-0 h-4 shrink-0"
            style={{ backgroundColor: `${meta.fill}15`, color: meta.fill }}
          >
            {meta.label}
          </Badge>
          {agent.has_override && (
            <Badge variant="default" className="text-[10px] px-1.5 py-0 h-4">
              override
            </Badge>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={onClose}
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Panel body */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-5">
        {/* Description */}
        <div className="space-y-1">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Description
          </h4>
          <p className="text-sm text-foreground leading-relaxed">
            {agent.description}
          </p>
        </div>

        <Separator />

        {/* Model Configuration */}
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Model
          </h4>
          <div className="flex items-center gap-2">
            <Select value={agent.effective_model} onValueChange={onModelChange}>
              <SelectTrigger className="h-8 text-xs flex-1">
                <SelectValue>
                  {stripProvider(agent.effective_model)}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {allowedModels.map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {isPending && (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground shrink-0" />
            )}
            {agent.has_override && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 shrink-0"
                    onClick={onReset}
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Reset to default</TooltipContent>
              </Tooltip>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: tierMeta.color }}
              />
              {tierMeta.label} tier
            </span>
            <Separator orientation="vertical" className="h-3" />
            <span>Default: {stripProvider(agent.default_model)}</span>
          </div>
        </div>

        <Separator />

        {/* Connections */}
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Workflow Connections
          </h4>

          {connections.upstream.length === 0 &&
            connections.downstream.length === 0 &&
            connections.loops.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No direct connections in the standard workflow
              </p>
            )}

          {connections.upstream.length > 0 && (
            <div className="space-y-1">
              <span className="text-[10px] text-muted-foreground font-medium flex items-center gap-1">
                <ArrowLeft className="h-2.5 w-2.5" />
                Receives from
              </span>
              <div className="flex flex-wrap gap-1">
                {connections.upstream.map((name) => {
                  const upAgent = allAgents.find((a) => a.name === name);
                  const upRole = upAgent ? deriveRole(upAgent) : "operations";
                  return (
                    <span
                      key={name}
                      className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs"
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${ROLE_META[upRole].dot}`}
                      />
                      {name}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {connections.downstream.length > 0 && (
            <div className="space-y-1">
              <span className="text-[10px] text-muted-foreground font-medium flex items-center gap-1">
                <ArrowRight className="h-2.5 w-2.5" />
                Sends to
              </span>
              <div className="flex flex-wrap gap-1">
                {connections.downstream.map((name) => {
                  const downAgent = allAgents.find((a) => a.name === name);
                  const downRole = downAgent
                    ? deriveRole(downAgent)
                    : "operations";
                  return (
                    <span
                      key={name}
                      className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs"
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${ROLE_META[downRole].dot}`}
                      />
                      {name}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {connections.loops.length > 0 && (
            <div className="space-y-1">
              <span className="text-[10px] text-muted-foreground font-medium flex items-center gap-1">
                <RefreshCw className="h-2.5 w-2.5" />
                Feedback loops
              </span>
              <div className="flex flex-wrap gap-1">
                {connections.loops.map((lp) => {
                  const lpAgent = allAgents.find((a) => a.name === lp.with);
                  const lpRole = lpAgent ? deriveRole(lpAgent) : "operations";
                  return (
                    <span
                      key={lp.with}
                      className="inline-flex items-center gap-1 rounded-md border border-dashed px-2 py-0.5 text-xs"
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${ROLE_META[lpRole].dot}`}
                      />
                      {lp.with}
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <Separator />

        {/* Role info */}
        <div className="space-y-1">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Role
          </h4>
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${meta.dot}`} />
            <span className={cn("text-sm font-medium", meta.text)}>
              {meta.label}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">{meta.description}</p>
        </div>
      </div>
    </div>
  );
}
