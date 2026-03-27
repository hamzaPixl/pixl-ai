/**
 * Reusable loading skeleton patterns.
 */

import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent } from '@/components/ui/card';

interface LoadingSkeletonsProps {
  count?: number;
  variant?: 'card' | 'row' | 'table-row';
}

export function LoadingSkeletons({ count = 5, variant = 'row' }: LoadingSkeletonsProps) {
  const items = Array.from({ length: count });

  if (variant === 'card') {
    return (
      <div className="space-y-2">
        {items.map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <Skeleton className="h-5 w-48 mb-2" />
              <Skeleton className="h-4 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (variant === 'table-row') {
    return (
      <>
        {items.map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </>
    );
  }

  // Default: simple rows
  return (
    <div className="space-y-3">
      {items.map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}
