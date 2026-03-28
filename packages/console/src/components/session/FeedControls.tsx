import { Wrench, Brain, MessageSquare, AlertTriangle, Search, Pin, PinOff, Zap, Shield, RefreshCw, FileCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { FeedFilters } from '@/hooks/use-session-feed-filters';

interface FeedControlsProps {
  totalCount: number;
  filteredCount: number;
  isLive: boolean;
  filters: FeedFilters;
  onFiltersChange: (filters: FeedFilters) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  autoScroll: boolean;
  onAutoScrollChange: (enabled: boolean) => void;
}

export function FeedControls({
  totalCount,
  filteredCount,
  isLive,
  filters,
  onFiltersChange,
  searchQuery,
  onSearchChange,
  autoScroll,
  onAutoScrollChange,
}: FeedControlsProps) {
  const toggleFilter = (key: keyof FeedFilters) => {
    onFiltersChange({ ...filters, [key]: !filters[key] });
  };

  return (
    <div className="flex flex-wrap items-center gap-2 p-2 border-b mb-2">
      {/* Event type filters */}
      <div className="flex items-center gap-1">
        <FilterToggle
          icon={<Wrench className="h-3 w-3" />}
          label="Tools"
          active={filters.showToolCalls}
          onClick={() => toggleFilter('showToolCalls')}
        />
        <FilterToggle
          icon={<Brain className="h-3 w-3" />}
          label="Think"
          active={filters.showThinking}
          onClick={() => toggleFilter('showThinking')}
        />
        <FilterToggle
          icon={<MessageSquare className="h-3 w-3" />}
          label="Text"
          active={filters.showText}
          onClick={() => toggleFilter('showText')}
        />
        <FilterToggle
          icon={<Zap className="h-3 w-3" />}
          label="Query"
          active={filters.showQueries}
          onClick={() => toggleFilter('showQueries')}
        />
        <FilterToggle
          icon={<AlertTriangle className="h-3 w-3" />}
          label="Errors"
          active={filters.showErrors}
          onClick={() => toggleFilter('showErrors')}
        />
        <FilterToggle
          icon={<Shield className="h-3 w-3" />}
          label="Gates"
          active={filters.showGates}
          onClick={() => toggleFilter('showGates')}
        />
        <FilterToggle
          icon={<RefreshCw className="h-3 w-3" />}
          label="Recovery"
          active={filters.showRecovery}
          onClick={() => toggleFilter('showRecovery')}
        />
        <FilterToggle
          icon={<FileCheck className="h-3 w-3" />}
          label="Contract"
          active={filters.showContracts}
          onClick={() => toggleFilter('showContracts')}
        />
      </div>

      {/* Search */}
      <div className="relative flex-1 min-w-[120px] max-w-[240px]">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
        <Input
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search events..."
          className="h-7 pl-7 text-xs"
        />
      </div>

      {/* Count */}
      <span className="text-xs text-muted-foreground">
        {filteredCount === totalCount
          ? `${totalCount} tasks`
          : `${filteredCount}/${totalCount} tasks`}
      </span>

      {/* Auto-scroll toggle */}
      {isLive && (
        <Button
          variant={autoScroll ? 'default' : 'outline'}
          size="sm"
          className="h-7 text-xs gap-1 ml-auto"
          onClick={() => onAutoScrollChange(!autoScroll)}
        >
          {autoScroll ? <Pin className="h-3 w-3" /> : <PinOff className="h-3 w-3" />}
          {autoScroll ? 'Following' : 'Scroll'}
        </Button>
      )}
    </div>
  );
}

function FilterToggle({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <Button
      variant={active ? 'default' : 'outline'}
      size="sm"
      className="h-6 text-[10px] gap-1 px-2"
      onClick={onClick}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </Button>
  );
}
