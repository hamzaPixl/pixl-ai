import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface BudgetBarProps {
  spent: number;
  limit: number;
  className?: string;
}

export function BudgetBar({ spent, limit, className }: BudgetBarProps) {
  const percentage = limit > 0 ? (spent / limit) * 100 : 0;
  const clampedWidth = Math.min(percentage, 100);
  const exceeded = percentage > 100;

  const barColor =
    percentage > 80
      ? "bg-red-500"
      : percentage > 60
        ? "bg-yellow-500"
        : "bg-green-500";

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center gap-2">
        <div className="relative h-2.5 flex-1 rounded-full bg-muted overflow-hidden">
          <div
            className={cn("absolute inset-y-0 left-0 rounded-full transition-all", barColor)}
            style={{ width: `${clampedWidth}%` }}
          />
          {/* 80% threshold line */}
          <div
            className="absolute inset-y-0 w-px border-l border-dashed border-foreground/40"
            style={{ left: "80%" }}
          />
        </div>
        {exceeded && (
          <Badge variant="destructive" className="text-[10px] px-1.5 py-0 leading-4 font-semibold">
            EXCEEDED
          </Badge>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        ${spent.toFixed(2)} / ${limit.toFixed(2)}
      </p>
    </div>
  );
}
