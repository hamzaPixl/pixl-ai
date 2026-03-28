import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  WorkItem,
  TransitionRecord,
  EpicWavesResponse,
} from "@/types/api";

const featureStatusColors: Record<string, string> = {
  backlog: "bg-muted text-muted-foreground",
  planned: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  in_progress:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
  review:
    "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  blocked: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  done: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
};

export interface EpicDetailTabsProps {
  projectId: string;
  features: WorkItem[] | undefined;
  waves: EpicWavesResponse | undefined;
  history: TransitionRecord[] | undefined;
  notes: string[] | undefined;
}

export function EpicDetailTabs({
  projectId,
  features,
  waves,
  history,
  notes,
}: EpicDetailTabsProps) {
  const totalFeatures = features?.length ?? 0;

  return (
    <Tabs defaultValue="features">
      <TabsList>
        <TabsTrigger value="features">Features ({totalFeatures})</TabsTrigger>
        <TabsTrigger value="waves">
          Waves ({waves?.total_waves ?? 0})
        </TabsTrigger>
        <TabsTrigger value="history">
          History ({history?.length ?? 0})
        </TabsTrigger>
        <TabsTrigger value="notes">Notes ({notes?.length ?? 0})</TabsTrigger>
      </TabsList>

      <TabsContent value="features" className="mt-4">
        {features && features.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Feature</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {features.map((f: WorkItem) => (
                <TableRow key={f.id}>
                  <TableCell>
                    <Link
                      to="/project/$projectId/features/$featureId"
                      params={{ projectId, featureId: f.id }}
                      className="text-primary underline text-sm"
                    >
                      {f.title}
                    </Link>
                    <span className="text-xs text-muted-foreground ml-2">
                      {f.id}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge className={featureStatusColors[f.status] ?? ""}>
                      {f.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-xs">
                      {f.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {new Date(f.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="text-sm text-muted-foreground py-8 text-center">
            No features in this epic yet.
          </p>
        )}
      </TabsContent>

      <TabsContent value="waves" className="mt-4">
        {waves && waves.waves && waves.waves.length > 0 ? (
          <div className="space-y-3">
            {waves.waves.map((waveFeatures, i) => (
              <Card key={i}>
                <CardHeader className="py-3">
                  <CardTitle className="text-sm">Wave {i + 1}</CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="space-y-1">
                    {waveFeatures.map((f) => (
                      <div
                        key={f.id}
                        className="flex items-center gap-2 text-sm"
                      >
                        <Badge
                          className={featureStatusColors[f.status ?? ""] ?? ""}
                          variant="outline"
                        >
                          {f.status ?? "pending"}
                        </Badge>
                        <Link
                          to="/project/$projectId/features/$featureId"
                          params={{ projectId, featureId: f.id }}
                          className="text-primary underline"
                        >
                          {f.title}
                        </Link>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-8 text-center">
            No wave data available. Decompose or run the epic to generate waves.
          </p>
        )}
      </TabsContent>

      <TabsContent value="history" className="mt-4">
        {history && history.length > 0 ? (
          <div className="space-y-3">
            {history.map((t: TransitionRecord) => (
              <div
                key={t.id}
                className="flex items-center gap-3 text-sm border-l-2 border-muted pl-4 py-1"
              >
                <span className="text-xs text-muted-foreground w-36 shrink-0">
                  {new Date(t.created_at).toLocaleString()}
                </span>
                <Badge variant="outline" className="text-xs">
                  {t.from_status ?? "—"}
                </Badge>
                <span className="text-muted-foreground">&rarr;</span>
                <Badge className="text-xs">{t.to_status}</Badge>
                {t.triggered_by && (
                  <span className="text-xs text-muted-foreground">
                    by {t.triggered_by}
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-8 text-center">
            No state transitions recorded.
          </p>
        )}
      </TabsContent>

      <TabsContent value="notes" className="mt-4">
        {notes && notes.length > 0 ? (
          <div className="space-y-2">
            {notes.map((note: string, i: number) => (
              <div
                key={i}
                className="text-sm border rounded-md px-3 py-2 bg-muted/30"
              >
                {note}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No notes yet.
          </p>
        )}
      </TabsContent>
    </Tabs>
  );
}
