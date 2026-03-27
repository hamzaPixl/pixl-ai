import { useState, useMemo } from 'react';
import type { TaskTreeNode, TraceEventNode } from '@/lib/session-utils';

export interface FeedFilters {
  showToolCalls: boolean;
  showThinking: boolean;
  showText: boolean;
  showErrors: boolean;
  showQueries: boolean;
  showGates: boolean;
  showRecovery: boolean;
  showContracts: boolean;
}

const DEFAULT_FILTERS: FeedFilters = {
  showToolCalls: true,
  showThinking: true,
  showText: true,
  showErrors: true,
  showQueries: true,
  showGates: true,
  showRecovery: true,
  showContracts: true,
};

function matchesFilter(child: TraceEventNode, filters: FeedFilters): boolean {
  switch (child.kind) {
    case 'tool': return filters.showToolCalls;
    case 'thinking': return filters.showThinking;
    case 'text': return filters.showText;
    case 'error': return filters.showErrors;
    case 'query': return filters.showQueries;
    case 'gate': return filters.showGates;
    case 'recovery': return filters.showRecovery;
    case 'contract': return filters.showContracts;
  }
}

function getSearchableText(child: TraceEventNode): string {
  switch (child.kind) {
    case 'tool': return [child.toolName, child.errorMessage].filter(Boolean).join(' ');
    case 'thinking': return child.text || '';
    case 'text': return child.text || '';
    case 'error': return [child.error, child.errorType].filter(Boolean).join(' ');
    case 'query': return [child.model, child.promptPreview].filter(Boolean).join(' ');
    case 'gate': return [child.gateAction, child.approver, child.reason].filter(Boolean).join(' ');
    case 'recovery': return [child.recoveryAction, child.action, child.decisionReason].filter(Boolean).join(' ');
    case 'contract': return [child.contractAction, child.check, child.warning, ...(child.violations || [])].filter(Boolean).join(' ');
  }
}

export function useSessionFeedFilters(taskTree: TaskTreeNode[]) {
  const [filters, setFilters] = useState<FeedFilters>(DEFAULT_FILTERS);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredTaskTree = useMemo(() => {
    const query = searchQuery.toLowerCase().trim();

    return taskTree.map((task) => {
      const filteredChildren = task.children.filter((child) => {
        if (!matchesFilter(child, filters)) return false;

        if (query) {
          const searchable = getSearchableText(child).toLowerCase();
          if (!searchable.includes(query)) return false;
        }

        return true;
      });

      return { ...task, children: filteredChildren };
    }).filter((task) => {
      if (query && !task.nodeId.toLowerCase().includes(query) && task.children.length === 0) {
        return false;
      }
      return true;
    });
  }, [taskTree, filters, searchQuery]);

  return {
    filters,
    setFilters,
    searchQuery,
    setSearchQuery,
    filteredTaskTree,
  };
}
