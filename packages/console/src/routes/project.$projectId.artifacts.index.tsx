/**
 * Artifacts list page — project-wide browse with pagination, search, type filter.
 *
 * Clicking a row navigates to the artifact detail page.
 */

import { createFileRoute, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { artifacts } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { LoadingSkeletons } from "@/components/loading-skeletons";
import { PaginationControls } from "@/components/pagination-controls";
import { Search, FileText, X } from "lucide-react";
import type { ArtifactMetadata, ArtifactType } from "@/types/api";

export const Route = createFileRoute("/project/$projectId/artifacts/")({
  beforeLoad: ({ params }) => {
    throw redirect({
      to: "/project/$projectId/insights",
      params,
      search: { tab: "artifacts" },
    });
  },
  component: ArtifactsIndexPage,
});

const PAGE_SIZE = 30;

const ARTIFACT_TYPES: ArtifactType[] = [
  "code",
  "test",
  "plan",
  "review",
  "document",
  "context",
  "requirement",
  "diagram",
  "log",
  "progress",
  "other",
];

function ArtifactsIndexPage() {
  const { projectId } = Route.useParams();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [page, setPage] = useState(0);

  const isSearching = search.trim().length > 0;
  const listParams = {
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    ...(typeFilter !== "all" ? { artifact_type: typeFilter } : {}),
  };

  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: queryKeys.artifacts.list(projectId, listParams),
    queryFn: () => artifacts.list(listParams),
    enabled: !isSearching,
  });

  const { data: searchData, isLoading: searchLoading } = useQuery({
    queryKey: queryKeys.artifacts.search(projectId, search, {
      artifact_type: typeFilter !== "all" ? typeFilter : undefined,
    }),
    queryFn: () =>
      artifacts.search(search, {
        artifact_type: typeFilter !== "all" ? typeFilter : undefined,
      }),
    enabled: isSearching,
  });

  const data = isSearching ? searchData : listData;
  const isLoading = isSearching ? searchLoading : listLoading;

  const hasNextPage = !isSearching && (data?.length ?? 0) === PAGE_SIZE;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Artifacts"
        description="Browse and search all artifacts across sessions"
      />

      {/* Search + Filter bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search artifacts (full-text)..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
            className="pl-9"
          />
          {search && (
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6"
              onClick={() => {
                setSearch("");
                setPage(0);
              }}
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
        <Select
          value={typeFilter}
          onValueChange={(v) => {
            setTypeFilter(v);
            setPage(0);
          }}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {ARTIFACT_TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                {t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Results count */}
      {data && (
        <p className="text-sm text-muted-foreground">
          {data.length} artifact{data.length !== 1 ? "s" : ""}
          {isSearching && ` for "${search}"`}
          {!isSearching && ` (page ${page + 1})`}
        </p>
      )}

      {/* Table */}
      {isLoading ? (
        <LoadingSkeletons count={8} />
      ) : data && data.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Session</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((a: ArtifactMetadata) => (
              <TableRow
                key={a.id}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => {}}
              >
                <TableCell>
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="font-mono text-xs truncate max-w-xs">
                      {a.name || a.path || a.id}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs">
                    {a.type}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">
                  {a.session_id}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {a.size_bytes
                    ? `${(a.size_bytes / 1024).toFixed(1)} KB`
                    : "\u2014"}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {new Date(a.created_at).toLocaleString()}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <EmptyState
          icon={FileText}
          title={
            isSearching
              ? `No artifacts matching "${search}"`
              : "No artifacts yet"
          }
        />
      )}

      {/* Pagination controls */}
      {!isSearching && (
        <PaginationControls
          page={page}
          onPageChange={setPage}
          hasNextPage={hasNextPage}
        />
      )}
    </div>
  );
}
