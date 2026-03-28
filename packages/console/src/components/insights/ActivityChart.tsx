import { useMemo } from "react";
import { useEvents } from "@/hooks/queries";
import { BarChart, Bar, XAxis, YAxis, Cell } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Activity } from "lucide-react";
import { EVENT_CATEGORIES } from "@/lib/insights-constants";


const CATEGORY_COLORS: Record<string, string> = {
  Session: "#2563eb",
  Task: "#16a34a",
  Gate: "#d97706",
  Artifact: "#7c3aed",
  Recovery: "#dc2626",
  Contract: "#0891b2",
  Entity: "#db2777",
  Other: "#94a3b8",
};

function eventCategory(type: string): string {
  for (const [cat, types] of Object.entries(EVENT_CATEGORIES)) {
    if ((types as string[]).includes(type)) return cat;
  }
  return "Other";
}

type EventBar = {
  id: string;
  name: string;
  category: string;
  color: string;
  timestamp: string;
  /** Running count: how many events of this category seen so far (gives height variation) */
  weight: number;
};

export function ActivityChart() {
  const { data: eventList, isLoading } = useEvents(
    { limit: 500, offset: 0 },
    true,
  );

  const events = useMemo(() => eventList ?? [], [eventList]);

  const chartData = useMemo<EventBar[]>(() => {
    return events.map((e) => {
      const cat = eventCategory(e.type);
      return {
        id: e.id,
        name: e.type.replace(/_/g, " "),
        category: cat,
        color: CATEGORY_COLORS[cat] ?? "#94a3b8",
        timestamp: e.timestamp,
        weight: 1,
      };
    });
  }, [events]);

  const { breakdown, totalCount } = useMemo(() => {
    const counts = new Map<string, number>();
    for (const d of chartData) {
      counts.set(d.category, (counts.get(d.category) ?? 0) + 1);
    }
    const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
    return {
      breakdown: sorted.map(([cat, count]) => ({
        category: cat,
        count,
        color: CATEGORY_COLORS[cat] ?? "#94a3b8",
      })),
      totalCount: chartData.length,
    };
  }, [chartData]);

  const chartConfig = useMemo<ChartConfig>(
    () => ({ events: { label: "Events" }, weight: { label: "Count" } }),
    [],
  );

  if (isLoading) return <Skeleton className="h-52" />;
  if (events.length === 0)
    return <EmptyState icon={Activity} title="No events to display" />;

  return (
    <div className="rounded-lg border border-border p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium text-muted-foreground">
          All events
        </h3>
        <span className="text-xs text-muted-foreground/70 tabular-nums">
          {totalCount} total
        </span>
      </div>
      <ChartContainer config={chartConfig} className="h-64 w-full">
        <BarChart data={chartData}>
          <XAxis dataKey="name" hide />
          <YAxis hide domain={[0, 1]} />
          <ChartTooltip
            cursor={false}
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const d = payload[0].payload as EventBar;
              const ts = new Date(d.timestamp);
              return (
                <div className="rounded-lg border border-border bg-background px-3 py-2 text-xs shadow-md space-y-1">
                  <p className="font-medium">{d.name}</p>
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ backgroundColor: d.color }}
                    />
                    {d.category} · {ts.toLocaleString()}
                  </div>
                </div>
              );
            }}
          />
          <Bar dataKey="weight" radius={[3, 3, 0, 0]}>
            {chartData.map((entry) => (
              <Cell key={entry.id} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ChartContainer>

      {/* Category legend bar */}
      {breakdown.length > 0 && (
        <div className="space-y-3">
          <div className="flex h-2 w-full overflow-hidden rounded-full">
            {breakdown.map((b) => (
              <div
                key={b.category}
                className="h-full transition-all"
                style={{
                  backgroundColor: b.color,
                  width: `${(b.count / totalCount) * 100}%`,
                }}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5">
            {breakdown.map((b) => (
              <div
                key={b.category}
                className="flex items-center gap-1.5 text-xs"
              >
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: b.color }}
                />
                <span className="font-medium">{b.category}</span>
                <span className="text-muted-foreground tabular-nums">
                  {((b.count / totalCount) * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
