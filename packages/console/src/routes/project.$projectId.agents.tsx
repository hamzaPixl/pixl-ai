/**
 * Agents page — roadmap-style flat list with inline detail expansion.
 *
 * Clicking an agent row expands a detail panel directly below it
 * (no sidebar sheet). Clicking again or clicking another agent collapses it.
 */

import { createFileRoute } from "@tanstack/react-router";
import { useState, useMemo, useCallback } from "react";
import {
  useAgents,
  useAllowedModels,
  useUpdateAgentModel,
} from "@/hooks/queries";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
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
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent } from "@/components/ui/card";
import {
  Bot,
  ChevronRight,
  ChevronDown,
  Cpu,
  RotateCcw,
  Loader2,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  type RoleKey,
  ROLE_META,
  ROLE_ORDER,
  deriveRole,
  deriveTier,
  TIER_META,
  stripProvider,
  getAgentConnections,
} from "@/lib/agent-utils";
import type { AgentInfo } from "@/types/api";

export const Route = createFileRoute("/project/$projectId/agents")({
  component: AgentsPage,
});

export function AgentsPageContent({ projectId }: { projectId: string }) {
  return <AgentsPageInner projectId={projectId} />;
}

function AgentsPage() {
  const { projectId } = Route.useParams();
  return <AgentsPageInner projectId={projectId} />;
}

function AgentsPageInner({ projectId }: { projectId: string }) {
  const { data: agentsList, isLoading } = useAgents(projectId);
  const { data: allowedModels } = useAllowedModels(projectId);
  const updateModel = useUpdateAgentModel(projectId);

  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(
    new Set(),
  );

  const handleModelChange = useCallback(
    (agent: AgentInfo, newModel: string) => {
      updateModel.mutate({ agentName: agent.name, model: newModel });
    },
    [updateModel],
  );

  const handleReset = useCallback(
    (agent: AgentInfo) => {
      updateModel.mutate({ agentName: agent.name, model: null });
    },
    [updateModel],
  );

  const grouped = useMemo(() => {
    if (!agentsList) return null;
    const map: Record<RoleKey, AgentInfo[]> = {
      strategy: [],
      implementation: [],
      testing: [],
      review: [],
      operations: [],
    };
    for (const agent of agentsList) {
      map[deriveRole(agent)].push(agent);
    }
    for (const key of ROLE_ORDER) {
      map[key].sort((a, b) => a.name.localeCompare(b.name));
    }
    return map;
  }, [agentsList]);

  const roleSummary = useMemo(() => {
    if (!grouped) return "";
    return ROLE_ORDER.filter((rk) => grouped[rk].length > 0)
      .map(
        (rk) =>
          `${grouped[rk].length} ${ROLE_META[rk].label.toLowerCase()}`,
      )
      .join(" \u00b7 ");
  }, [grouped]);

  const toggleSection = (key: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleAgent = (name: string) => {
    setSelectedAgent((prev) => (prev === name ? null : name));
  };

  return (
    <TooltipProvider>
      <div className="space-y-4">
        <PageHeader
          title="Agents"
          description={`Configure agent models and view role assignments.${roleSummary ? ` ${roleSummary}` : ""}`}
        />

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <Skeleton className="h-5 w-48 mb-2" />
                  <Skeleton className="h-4 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : !grouped ? (
          <EmptyState
            icon={Bot}
            title="No agents found"
            description="Make sure the project is initialized with pixl init."
          />
        ) : (
          <div className="space-y-1">
            {ROLE_ORDER.map((rk) => {
              const roleAgents = grouped[rk];
              if (roleAgents.length === 0) return null;
              const meta = ROLE_META[rk];
              const collapsed = collapsedSections.has(rk);

              return (
                <div key={rk}>
                  <button
                    type="button"
                    onClick={() => toggleSection(rk)}
                    className="flex items-center gap-2 w-full px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {collapsed ? (
                      <ChevronRight className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5" />
                    )}
                    <span
                      className={cn(
                        "h-2 w-2 rounded-full shrink-0",
                        meta.dot,
                      )}
                    />
                    <span className="uppercase tracking-wider">
                      {meta.label}
                    </span>
                    <span className="text-muted-foreground/60 tabular-nums">
                      {roleAgents.length}
                    </span>
                  </button>

                  {!collapsed && (
                    <div className="space-y-px">
                      {roleAgents.map((agent) => {
                        const isOpen = selectedAgent === agent.name;
                        return (
                          <div
                            key={agent.name}
                            className={cn(
                              "rounded-lg transition-all duration-200",
                              isOpen && "border border-highlight/20 bg-card",
                            )}
                          >
                            <AgentRow
                              agent={agent}
                              isOpen={isOpen}
                              onToggle={() => toggleAgent(agent.name)}
                            />
                            {isOpen && (
                              <AgentInlineDetail
                                agent={agent}
                                allowedModels={allowedModels ?? []}
                                allAgents={agentsList ?? []}
                                isPending={updateModel.isPending}
                                onModelChange={(m) =>
                                  handleModelChange(agent, m)
                                }
                                onReset={() => handleReset(agent)}
                              />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}

/* ── Agent row ─────────── */

function AgentRow({
  agent,
  isOpen,
  onToggle,
}: {
  agent: AgentInfo;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      onClick={onToggle}
      className={cn(
        "group flex items-center gap-3 px-3 py-2.5 rounded-md cursor-pointer transition-all duration-200 border",
        isOpen
          ? "bg-transparent border-transparent"
          : "border-transparent hover:bg-muted/50 hover:border-border",
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          "shrink-0 p-1.5 rounded-md transition-colors",
          isOpen ? "bg-highlight/10" : "bg-muted",
        )}
      >
        <Bot
          className={cn(
            "h-4 w-4",
            isOpen ? "text-highlight" : "text-muted-foreground",
          )}
        />
      </div>

      {/* Name + description */}
      <div className="flex-1 min-w-0">
        <span
          className={cn(
            "font-medium text-sm",
            isOpen && "text-highlight",
          )}
        >
          {agent.name}
        </span>
        {agent.description && (
          <p className="text-xs text-muted-foreground/60 truncate mt-0.5">
            {agent.description}
          </p>
        )}
      </div>

      {/* Right metadata */}
      <div className="flex items-center gap-2.5 shrink-0 opacity-70 group-hover:opacity-100 transition-opacity">
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="text-xs text-muted-foreground tabular-nums flex items-center gap-1 font-mono">
              <Cpu className="h-3 w-3" />
              {stripProvider(agent.effective_model)}
            </span>
          </TooltipTrigger>
          <TooltipContent>Effective model</TooltipContent>
        </Tooltip>

        {agent.has_override && (
          <Badge
            variant="default"
            className="text-[10px] px-1.5 py-0 h-4 bg-highlight text-highlight-foreground"
          >
            override
          </Badge>
        )}

        {isOpen ? (
          <ChevronDown className="h-4 w-4 text-highlight" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        )}
      </div>
    </div>
  );
}

/* ── Inline detail panel (expands below row) ─────────── */

function AgentInlineDetail({
  agent,
  allowedModels,
  allAgents,
  isPending,
  onModelChange,
  onReset,
}: {
  agent: AgentInfo;
  allowedModels: string[];
  allAgents: AgentInfo[];
  isPending: boolean;
  onModelChange: (model: string) => void;
  onReset: () => void;
}) {
  const role = deriveRole(agent);
  const meta = ROLE_META[role];
  const tier = deriveTier(agent.effective_model);
  const tierMeta = TIER_META[tier];
  const connections = getAgentConnections(agent.name);

  return (
    <div className="px-5 pb-5 pt-2 space-y-5 animate-in slide-in-from-top-2 fade-in duration-200">
      {/* Model config */}
      <div className="space-y-3">
        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Model Configuration
        </h4>
        <div className="flex items-center gap-3">
          <Select value={agent.effective_model} onValueChange={onModelChange}>
            <SelectTrigger className="h-9 text-sm flex-1 max-w-xs">
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
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground shrink-0" />
          )}
          {agent.has_override && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-9 gap-1.5"
                  onClick={(e) => {
                    e.stopPropagation();
                    onReset();
                  }}
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Reset
                </Button>
              </TooltipTrigger>
              <TooltipContent>Reset to default model</TooltipContent>
            </Tooltip>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: tierMeta.color }}
            />
            {tierMeta.label} tier
          </span>
          <span>Default: {stripProvider(agent.default_model)}</span>
        </div>
      </div>

      {/* Connections */}
      {(connections.upstream.length > 0 ||
        connections.downstream.length > 0 ||
        connections.loops.length > 0) && (
        <>
          <Separator />
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Workflow Connections
            </h4>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {connections.upstream.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                    <ArrowLeft className="h-3 w-3" />
                    Receives from
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {connections.upstream.map((name) => {
                      const upAgent = allAgents.find((a) => a.name === name);
                      const upRole = upAgent
                        ? deriveRole(upAgent)
                        : "operations";
                      return (
                        <span
                          key={name}
                          className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs"
                        >
                          <span
                            className={cn(
                              "h-1.5 w-1.5 rounded-full",
                              ROLE_META[upRole].dot,
                            )}
                          />
                          {name}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {connections.downstream.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                    <ArrowRight className="h-3 w-3" />
                    Sends to
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {connections.downstream.map((name) => {
                      const downAgent = allAgents.find((a) => a.name === name);
                      const downRole = downAgent
                        ? deriveRole(downAgent)
                        : "operations";
                      return (
                        <span
                          key={name}
                          className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs"
                        >
                          <span
                            className={cn(
                              "h-1.5 w-1.5 rounded-full",
                              ROLE_META[downRole].dot,
                            )}
                          />
                          {name}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {connections.loops.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                    <RefreshCw className="h-3 w-3" />
                    Feedback loops
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {connections.loops.map((lp) => {
                      const lpAgent = allAgents.find(
                        (a) => a.name === lp.with,
                      );
                      const lpRole = lpAgent
                        ? deriveRole(lpAgent)
                        : "operations";
                      return (
                        <span
                          key={lp.with}
                          className="inline-flex items-center gap-1.5 rounded-md border border-dashed px-2.5 py-1 text-xs"
                        >
                          <span
                            className={cn(
                              "h-1.5 w-1.5 rounded-full",
                              ROLE_META[lpRole].dot,
                            )}
                          />
                          {lp.with}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Role info */}
      <Separator />
      <div className="space-y-1.5">
        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Role
        </h4>
        <div className="flex items-center gap-2">
          <span className={cn("h-2.5 w-2.5 rounded-full", meta.dot)} />
          <span className={cn("text-sm font-medium", meta.text)}>
            {meta.label}
          </span>
        </div>
        <p className="text-sm text-muted-foreground">{meta.description}</p>
      </div>
    </div>
  );
}
