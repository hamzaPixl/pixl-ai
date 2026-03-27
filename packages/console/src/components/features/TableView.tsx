import type { Feature, SessionListEntry } from "@/types/api";
import { groupFeatures, type GroupBy } from "@/lib/feature-utils";
import { FeatureTable } from "@/components/features/FeatureTable";
import { ChevronDown, ChevronRight } from "lucide-react";
import { flexRender, useReactTable } from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export interface TableViewProps {
  table: ReturnType<typeof useReactTable<Feature>>;
  groupBy: GroupBy;
  features: Feature[];
  projectId: string;
  sessionsByFeature: Map<string, SessionListEntry[]>;
  collapsedGroups: Set<string>;
  onToggleGroup: (key: string) => void;
  onFeatureClick: (feature: Feature) => void;
  onRunClick: (e: React.MouseEvent, feature: Feature) => void;
}

export function TableView({
  table,
  groupBy,
  features,
  projectId,
  sessionsByFeature,
  collapsedGroups,
  onToggleGroup,
  onFeatureClick,
  onRunClick,
}: TableViewProps) {
  if (groupBy !== "none") {
    const groups = groupFeatures(features, groupBy);
    return (
      <div className="space-y-4">
        {groups.map((group) => (
          <div key={group.key}>
            <button
              type="button"
              className="flex items-center gap-2 w-full text-left mb-2"
              aria-expanded={!collapsedGroups.has(group.key)}
              onClick={() => onToggleGroup(group.key)}
            >
              {collapsedGroups.has(group.key) ? (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {group.label}
              </span>
              <span className="text-xs text-muted-foreground">
                ({group.features.length})
              </span>
              <div className="flex-1 border-t border-border" />
            </button>
            {!collapsedGroups.has(group.key) && (
              <FeatureTable
                features={group.features}
                projectId={projectId}
                onFeatureClick={onFeatureClick}
                onRunClick={onRunClick}
                sessionsByFeature={sessionsByFeature}
              />
            )}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  style={{
                    width:
                      header.getSize() !== 150 ? header.getSize() : undefined,
                  }}
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow
              key={row.id}
              className="cursor-pointer"
              tabIndex={0}
              role="link"
              onClick={() => onFeatureClick(row.original)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onFeatureClick(row.original);
                }
              }}
            >
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
