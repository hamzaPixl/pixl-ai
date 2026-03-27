/**
 * Events / Activity Feed page.
 *
 * Project-wide activity timeline with filtering by type, session, and
 * date range. Shows event counts summary and expandable event detail.
 */

import { createFileRoute, redirect } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import {
  useEvents,
  useEventCounts,
} from '@/hooks/queries';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { PageHeader } from '@/components/page-header';
import { EmptyState } from '@/components/empty-state';
import { LoadingSkeletons } from '@/components/loading-skeletons';
import { PaginationControls } from '@/components/pagination-controls';
import { Activity, ChevronDown, Filter, X } from 'lucide-react';
import type { Event } from '@/types/api';

export const Route = createFileRoute('/project/$projectId/events')({
  beforeLoad: ({ params }) => {
    throw redirect({ to: '/project/$projectId/insights', params, search: { tab: 'activity' } });
  },
  component: EventsPage,
});

const PAGE_SIZE = 50;

const EVENT_CATEGORIES: Record<string, string[]> = {
  Session: [
    'session_created',
    'session_started',
    'session_paused',
    'session_resumed',
    'session_completed',
    'session_failed',
    'session_cancelled',
    'session_reclaimed',
  ],
  Task: [
    'task_started',
    'task_completed',
    'task_failed',
    'task_skipped',
    'task_blocked',
    'task_unblocked',
    'task_retry_queued',
    'task_paused',
    'task_rolled_back',
  ],
  Gate: [
    'gate_requested',
    'gate_approved',
    'gate_rejected',
    'gate_timeout',
  ],
  Artifact: [
    'artifact_created',
    'artifact_modified',
    'artifact_frozen',
  ],
  Recovery: [
    'recovery_requested',
    'recovery_decision',
    'recovery_succeeded',
    'recovery_failed',
    'recovery_escalated',
  ],
  Contract: [
    'contract_violation',
    'contract_warning',
    'contract_passed',
  ],
  Entity: [
    'entity_status_changed',
    'feature_created',
    'feature_updated',
    'epic_created',
    'epic_updated',
    'roadmap_created',
  ],
};

const eventTypeColor: Record<string, string> = {
  session_completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  session_failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  task_completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  task_failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  gate_approved: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  gate_rejected: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  contract_violation: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  recovery_escalated: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
};

function EventsPage() {
  Route.useParams(); // ensure route context
  const [page, setPage] = useState(0);
  const [sessionFilter, setSessionFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');

  useEffect(() => setPage(0), [sessionFilter]);

  const params = {
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    ...(sessionFilter ? { session_id: sessionFilter } : {}),
  };

  const { data: eventList, isLoading } = useEvents(params, true);
  const { data: counts } = useEventCounts();

  const hasNextPage = (eventList?.length ?? 0) === PAGE_SIZE;

  // Client-side category filter
  const filteredEvents = eventList?.filter((e: Event) => {
    if (categoryFilter === 'all') return true;
    const types = EVENT_CATEGORIES[categoryFilter];
    return types?.includes(e.type);
  });

  // Top counts for summary
  const topCounts = counts
    ? Object.entries(counts)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 8)
    : [];

  return (
    <div className="space-y-6">
      <PageHeader title="Activity" description="Project-wide event timeline and activity feed" />

      {/* Event count summary */}
      {topCounts.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {topCounts.map(([type, count]) => (
            <Badge key={type} variant="outline" className="text-xs">
              {type.replace(/_/g, ' ')}: {count}
            </Badge>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative max-w-xs">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Filter by session ID..."
            value={sessionFilter}
            onChange={(e) => setSessionFilter(e.target.value)}
            className="pl-9"
          />
          {sessionFilter && (
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6"
              onClick={() => setSessionFilter('')}
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
        <Select
          value={categoryFilter}
          onValueChange={(v) => { setCategoryFilter(v); setPage(0); }}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {Object.keys(EVENT_CATEGORIES).map((cat) => (
              <SelectItem key={cat} value={cat}>
                {cat}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Event timeline */}
      {isLoading ? (
        <LoadingSkeletons count={10} />
      ) : filteredEvents && filteredEvents.length > 0 ? (
        <div className="space-y-1">
          {filteredEvents.map((event: Event) => (
            <EventRow key={event.id} event={event} />
          ))}
        </div>
      ) : (
        <EmptyState icon={Activity} title="No events to display" />
      )}

      <PaginationControls page={page} onPageChange={setPage} hasNextPage={hasNextPage} />
    </div>
  );
}

function EventRow({ event }: { event: Event }) {
  const colorClass =
    eventTypeColor[event.type] ?? 'bg-muted text-muted-foreground';
  const hasData = event.data && Object.keys(event.data).length > 0;

  return (
    <Collapsible>
      <CollapsibleTrigger asChild>
        <div className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted/50 cursor-pointer text-sm">
          <span className="text-xs text-muted-foreground w-36 shrink-0">
            {new Date(event.timestamp).toLocaleString()}
          </span>
          <Badge className={`text-xs ${colorClass}`}>
            {event.type.replace(/_/g, ' ')}
          </Badge>
          {event.session_id && (
            <span className="font-mono text-xs text-muted-foreground">
              {event.session_id}
            </span>
          )}
          {event.node_id && (
            <span className="font-mono text-xs text-muted-foreground">
              → {event.node_id}
            </span>
          )}
          {hasData && (
            <ChevronDown className="h-3 w-3 ml-auto text-muted-foreground" />
          )}
        </div>
      </CollapsibleTrigger>
      {hasData && (
        <CollapsibleContent>
          <pre className="bg-muted rounded-md p-3 mx-3 mb-2 text-xs overflow-x-auto max-h-48">
            {JSON.stringify(event.data, null, 2)}
          </pre>
        </CollapsibleContent>
      )}
    </Collapsible>
  );
}
