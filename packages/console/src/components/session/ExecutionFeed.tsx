import { useRef, useEffect } from 'react';
import { Clock, RefreshCw } from 'lucide-react';
import { TaskTraceBlock } from './TaskTraceBlock';
import { FeedControls } from './FeedControls';
import { useSessionFeedFilters } from '@/hooks/use-session-feed-filters';
import type { TaskTreeNode } from '@/lib/session-utils';

interface ExecutionFeedProps {
  taskTree: TaskTreeNode[];
  eventCount: number;
  isLive: boolean;
  isConnected: boolean;
  isLoadingHistory: boolean;
  autoScroll: boolean;
  onAutoScrollChange: (enabled: boolean) => void;
}

export function ExecutionFeed({
  taskTree,
  eventCount,
  isLive,
  isConnected,
  isLoadingHistory,
  autoScroll,
  onAutoScrollChange,
}: ExecutionFeedProps) {
  const traceEndRef = useRef<HTMLDivElement>(null);
  const { filters, setFilters, searchQuery, setSearchQuery, filteredTaskTree } =
    useSessionFeedFilters(taskTree);

  useEffect(() => {
    if (autoScroll && isLive && traceEndRef.current) {
      traceEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [eventCount, isLive, autoScroll]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-w-0">
      <div className="text-sm font-medium text-muted-foreground mb-2">
        {isLive ? 'LIVE TRACE' : 'EXECUTION TRACE'} ({eventCount} events)
      </div>

      <FeedControls
        totalCount={taskTree.length}
        filteredCount={filteredTaskTree.length}
        isLive={isLive}
        filters={filters}
        onFiltersChange={setFilters}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        autoScroll={autoScroll}
        onAutoScrollChange={onAutoScrollChange}
      />

      <div className="flex-1 overflow-y-auto rounded-md border bg-muted/20 p-4" role="log" aria-live="polite">
        {filteredTaskTree.length === 0 && taskTree.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            {isLoadingHistory ? (
              <>
                <RefreshCw className="h-8 w-8 mb-2 animate-spin" />
                <p>Loading execution trace...</p>
              </>
            ) : isLive && isConnected ? (
              <>
                <Clock className="h-8 w-8 mb-2" />
                <p>Waiting for events...</p>
              </>
            ) : isLive ? (
              <>
                <RefreshCw className="h-8 w-8 mb-2 animate-spin" />
                <p>Connecting to event stream...</p>
              </>
            ) : (
              <>
                <Clock className="h-8 w-8 mb-2" />
                <p>No trace events recorded</p>
              </>
            )}
          </div>
        ) : filteredTaskTree.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <p>No events match current filters</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredTaskTree.map((task) => (
              <TaskTraceBlock key={task.nodeId} task={task} />
            ))}
            <div ref={traceEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
