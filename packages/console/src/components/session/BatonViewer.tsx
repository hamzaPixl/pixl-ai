import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { formatTimeAgo } from "@/lib/format-utils";
import type { BatonState, BatonHistoryEntry } from "@/types/api";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </h4>
      {children}
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <p className="text-xs text-muted-foreground italic">None</p>
    );
  }
  return (
    <ul className="space-y-0.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-1.5 text-sm">
          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-foreground/40" />
          {item}
        </li>
      ))}
    </ul>
  );
}

function BatonContent({ baton }: { baton: BatonState }) {
  return (
    <div className="space-y-4">
      <div>
        <p className="text-base font-semibold leading-snug">{baton.goal}</p>
      </div>

      <Section title="Current State">
        <BulletList items={baton.current_state} />
      </Section>

      {baton.decision_log.length > 0 && (
        <Section title="Decision Log">
          <BulletList items={baton.decision_log} />
        </Section>
      )}

      {baton.constraints.length > 0 && (
        <Section title="Constraints">
          <BulletList items={baton.constraints} />
        </Section>
      )}

      {baton.acceptance.length > 0 && (
        <Section title="Quality Signals">
          <div className="flex flex-wrap gap-1">
            {baton.acceptance.map((criterion, i) => (
              <Badge key={i} variant="outline" className="text-xs">
                {criterion}
              </Badge>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function HistoryTimeline({ history }: { history: BatonHistoryEntry[] }) {
  if (history.length === 0) return null;

  return (
    <div className="space-y-2">
      <Separator />
      <Section title="Baton History">
        <div className="space-y-3">
          {history.map((entry, i) => (
            <div
              key={i}
              className="flex items-start gap-2 border-l-2 border-muted pl-3"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-[10px]">
                    {entry.stage_id}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatTimeAgo(entry.timestamp)}
                  </span>
                </div>
                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                  {entry.baton.goal}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

export function BatonViewer({
  baton,
  history,
}: {
  baton: BatonState | null;
  history?: BatonHistoryEntry[];
}) {
  if (!baton) {
    return (
      <Card>
        <CardContent className="py-6">
          <p className="text-center text-sm text-muted-foreground">
            No baton context available
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Baton Context</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <BatonContent baton={baton} />
        {history && history.length > 0 && (
          <HistoryTimeline history={history} />
        )}
      </CardContent>
    </Card>
  );
}
