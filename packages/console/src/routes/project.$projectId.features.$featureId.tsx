/**
 * Feature detail page — sidebar + scrollable content layout.
 *
 * Left sidebar: status, metadata, links, dependencies.
 * Main area: description, success criteria, then collapsible sections
 * for sessions, artifacts, timeline, and notes.
 */

import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useQueryClient, useMutation, useQuery } from "@tanstack/react-query";
import { useFeature, useFeatureHistory, useSessions } from "@/hooks/queries";
import { features as featuresApi, artifacts as artifactsApi } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { toast } from "sonner";
import {
  ArrowLeft,
  Play,
  ChevronDown,
  DollarSign,
  Clock,
  GitBranch,
  ExternalLink,
  AlertTriangle,
} from "lucide-react";
import type { SessionListEntry } from "@/types/api";
import {
  SessionsTab,
  ArtifactsTab,
  TimelineTab,
  NotesTab,
  statusColors,
} from "@/components/features/FeatureDetail";

export const Route = createFileRoute("/project/$projectId/features/$featureId")(
  {
    component: FeatureDetailPage,
  },
);

/* ── Collapsible section wrapper ─────────────────────────── */

function Section({
  title,
  count,
  defaultOpen,
  children,
}: {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const hasContent = count === undefined || count > 0;
  return (
    <Collapsible defaultOpen={defaultOpen ?? hasContent}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 py-3 group text-left">
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground transition-transform group-data-[state=closed]:-rotate-90" />
        <span className="text-sm font-medium">{title}</span>
        {count !== undefined && (
          <span className="text-xs text-muted-foreground">({count})</span>
        )}
      </CollapsibleTrigger>
      <CollapsibleContent>{children}</CollapsibleContent>
    </Collapsible>
  );
}

/* ── Sidebar label/value pair ────────────────────────────── */

function SidebarField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground">{label}</p>
      <div className="text-sm">{children}</div>
    </div>
  );
}

/* ── Main page ───────────────────────────────────────────── */

function FeatureDetailPage() {
  const { projectId, featureId } = Route.useParams();
  const queryClient = useQueryClient();
  const [noteText, setNoteText] = useState("");

  const { data: feature, isLoading } = useFeature(featureId, projectId);
  const { data: history } = useFeatureHistory(featureId, projectId);
  const { data: allSessions } = useSessions(undefined, projectId);

  const featureSessions = allSessions?.filter(
    (s: SessionListEntry) => s.feature_id === featureId,
  );

  const { data: featureArtifacts } = useQuery({
    queryKey: queryKeys.artifacts.list(projectId, { feature_id: featureId }),
    queryFn: async () => {
      const results = await Promise.all(
        featureSessions!.map((s: SessionListEntry) =>
          artifactsApi.list({ session_id: s.id }),
        ),
      );
      return results.flat();
    },
    enabled: !!featureSessions && featureSessions.length > 0,
  });

  const addNoteMutation = useMutation({
    mutationFn: (note: string) => featuresApi.notes.add(featureId, note),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.features.detail(projectId, featureId),
      });
      setNoteText("");
      toast.success("Note added");
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="flex gap-8">
          <Skeleton className="h-96 w-72 shrink-0" />
          <Skeleton className="h-96 flex-1" />
        </div>
      </div>
    );
  }

  if (!feature) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-muted-foreground">Feature not found.</p>
        <Button variant="ghost" asChild className="mt-4">
          <Link to="/project/$projectId/features" params={{ projectId }}>
            Back to Features
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="space-y-3">
        <Link
          to="/project/$projectId/roadmap"
          params={{ projectId }}
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3 w-3" />
          Features
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-semibold tracking-tight truncate">
              {feature.title}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5 font-mono">
              {feature.id}
              {feature.epic_id && <> &middot; {feature.epic_id}</>}
            </p>
          </div>
          <Button size="sm">
            <Play className="h-3.5 w-3.5 mr-1.5" />
            Run
          </Button>
        </div>
      </div>

      {/* Sidebar + Main */}
      <div className="flex flex-col md:flex-row gap-5 md:gap-8">
        {/* ── Left sidebar ──────────────────────────────── */}
        <aside className="w-full md:w-56 shrink-0 space-y-4 md:space-y-5 md:self-start md:sticky md:top-6 rounded-lg border md:border-0 p-4 md:p-0">
          {/* Status / Priority / Type */}
          <div className="grid grid-cols-3 md:grid-cols-1 gap-3">
            <SidebarField label="Status">
              <Badge className={statusColors[feature.status] ?? ""}>
                {feature.status}
              </Badge>
            </SidebarField>
            <SidebarField label="Priority">
              <Badge variant="outline">{feature.priority}</Badge>
            </SidebarField>
            <SidebarField label="Type">
              <Badge variant="outline">{feature.type}</Badge>
            </SidebarField>
          </div>

          <div className="border-t border-border" />

          {/* Cost & Time */}
          <div className="grid grid-cols-2 md:grid-cols-1 gap-3">
            <SidebarField label="Cost">
              <span className="flex items-center gap-1.5">
                <DollarSign className="h-3.5 w-3.5 text-muted-foreground" />
                <span>${feature.total_cost_usd.toFixed(4)}</span>
                <span className="text-xs text-muted-foreground hidden md:inline">
                  ({feature.total_tokens.toLocaleString()})
                </span>
              </span>
            </SidebarField>
            <SidebarField label="Hours">
              <span className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                <span>
                  {feature.estimated_hours ?? "\u2014"}h est
                  {" / "}
                  {feature.actual_hours ?? "\u2014"}h actual
                </span>
              </span>
            </SidebarField>
          </div>

          {/* Links */}
          {(feature.branch_name || feature.pr_url) && (
            <>
              <div className="border-t border-border" />
              <div className="space-y-3">
                {feature.branch_name && (
                  <SidebarField label="Branch">
                    <span className="flex items-center gap-1.5">
                      <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="font-mono text-xs truncate">
                        {feature.branch_name}
                      </span>
                    </span>
                  </SidebarField>
                )}
                {feature.pr_url && (
                  <SidebarField label="Pull Request">
                    <a
                      href={feature.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 text-primary hover:underline text-xs"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      View PR
                    </a>
                  </SidebarField>
                )}
              </div>
            </>
          )}

          {/* Dependencies */}
          {feature.depends_on.length > 0 && (
            <>
              <div className="border-t border-border" />
              <SidebarField label="Depends On">
                <div className="flex gap-1 flex-wrap">
                  {feature.depends_on.map((dep: string) => (
                    <Badge
                      key={dep}
                      variant="outline"
                      className="text-xs font-mono"
                    >
                      {dep}
                    </Badge>
                  ))}
                </div>
              </SidebarField>
            </>
          )}

          {/* Blocked */}
          {feature.blocked_by && (
            <>
              <div className="border-t border-border" />
              <SidebarField label="Blocked By">
                <div className="flex items-start gap-1.5 text-red-600 dark:text-red-400">
                  <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                  <div>
                    <span className="text-xs font-mono">
                      {feature.blocked_by}
                    </span>
                    {feature.blocked_reason && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {feature.blocked_reason}
                      </p>
                    )}
                  </div>
                </div>
              </SidebarField>
            </>
          )}
        </aside>

        {/* ── Main content ──────────────────────────────── */}
        <main className="flex-1 min-w-0 space-y-1">
          {/* Description */}
          {feature.description && (
            <div className="pb-4">
              <p className="text-sm leading-relaxed">{feature.description}</p>
            </div>
          )}

          {/* Success Criteria */}
          {feature.success_criteria?.length > 0 && (
            <div className="pb-4">
              <p className="text-xs text-muted-foreground mb-2">
                Success Criteria
              </p>
              <ul className="space-y-1">
                {feature.success_criteria.map((c: string, i: number) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm"
                  >
                    <span className="text-muted-foreground mt-0.5">-</span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Assumptions */}
          {feature.assumptions?.length > 0 && (
            <div className="pb-2">
              <p className="text-xs text-muted-foreground mb-2">Assumptions</p>
              <ul className="space-y-1">
                {feature.assumptions.map((a: string, i: number) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <span className="mt-0.5">-</span>
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="border-t border-border" />

          {/* Sessions */}
          <Section
            title="Sessions"
            count={featureSessions?.length ?? 0}
          >
            <div className="pb-2">
              <SessionsTab sessions={featureSessions} projectId={projectId} />
            </div>
          </Section>

          <div className="border-t border-border" />

          {/* Artifacts */}
          <Section
            title="Artifacts"
            count={featureArtifacts?.length ?? 0}
          >
            <div className="pb-2">
              <ArtifactsTab
                artifacts={featureArtifacts}
                projectId={projectId}
              />
            </div>
          </Section>

          <div className="border-t border-border" />

          {/* Timeline */}
          <Section title="Timeline" count={history?.length ?? 0}>
            <div className="pb-2">
              <TimelineTab history={history} />
            </div>
          </Section>

          <div className="border-t border-border" />

          {/* Notes */}
          <Section
            title="Notes"
            count={feature.notes?.length ?? 0}
            defaultOpen
          >
            <div className="pb-2">
              <NotesTab
                notes={feature.notes}
                noteText={noteText}
                onNoteTextChange={setNoteText}
                onAddNote={() => addNoteMutation.mutate(noteText.trim())}
                isPending={addNoteMutation.isPending}
              />
            </div>
          </Section>
        </main>
      </div>
    </div>
  );
}
