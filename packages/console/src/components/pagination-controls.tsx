/**
 * Reusable offset-based pagination controls (Previous / Page N / Next).
 */

import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationControlsProps {
  page: number;
  onPageChange: (page: number) => void;
  hasNextPage: boolean;
}

export function PaginationControls({ page, onPageChange, hasNextPage }: PaginationControlsProps) {
  return (
    <div className="flex items-center justify-between">
      <Button
        variant="outline"
        size="sm"
        disabled={page === 0}
        onClick={() => onPageChange(Math.max(0, page - 1))}
      >
        <ChevronLeft className="h-4 w-4 mr-1" />
        Previous
      </Button>
      <span className="text-sm text-muted-foreground">Page {page + 1}</span>
      <Button
        variant="outline"
        size="sm"
        disabled={!hasNextPage}
        onClick={() => onPageChange(page + 1)}
      >
        Next
        <ChevronRight className="h-4 w-4 ml-1" />
      </Button>
    </div>
  );
}
