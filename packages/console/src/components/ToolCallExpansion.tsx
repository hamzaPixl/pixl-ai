/**
 * Tool Call Expansion - Expandable tool call detail view.
 *
 * Features:
 * - Expand/collapse tool call details
 * - Special handling for Edit tool with diff view
 * - File path highlighting
 * - Input/output preview
 */

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  ChevronDown,
  ChevronRight,
  Wrench,
  FileText,
  Terminal,
  Search,
  Edit3,
  FolderOpen,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";

export interface ToolCallData {
  id: string;
  toolName: string;
  toolInput: Record<string, unknown>;
  isError?: boolean;
  errorMessage?: string;
  timestamp: Date;
  lifecycle?: 'started' | 'running' | 'completed' | 'failed';
  duration?: number;
}

interface ToolCallExpansionProps {
  toolCall: ToolCallData;
  defaultExpanded?: boolean;
}

export function ToolCallExpansion({
  toolCall,
  defaultExpanded = false,
}: ToolCallExpansionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const toolIcons: Record<string, React.ReactNode> = {
    Read: <FileText className="h-3.5 w-3.5" />,
    Write: <Edit3 className="h-3.5 w-3.5" />,
    Edit: <Edit3 className="h-3.5 w-3.5" />,
    Bash: <Terminal className="h-3.5 w-3.5" />,
    Glob: <FolderOpen className="h-3.5 w-3.5" />,
    Grep: <Search className="h-3.5 w-3.5" />,
  };

  const icon = toolIcons[toolCall.toolName] || <Wrench className="h-3.5 w-3.5" />;

  // Format summary based on tool type
  const summary = formatToolSummary(toolCall.toolName, toolCall.toolInput);

  const isEditTool = toolCall.toolName === "Edit";
  const hasOldNewStrings =
    isEditTool &&
    typeof toolCall.toolInput.old_string === "string" &&
    typeof toolCall.toolInput.new_string === "string";

  return (
    <div className={cn(
      "border rounded-md bg-card",
      toolCall.lifecycle === 'running' && "border-amber-500/30 animate-pulse"
    )}>
      {/* Header - always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 p-2 text-left hover:bg-muted/50 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
        )}
        <span className="text-orange-500">{icon}</span>
        <span className="font-mono text-sm font-medium">{toolCall.toolName}</span>
        <span className="text-xs text-muted-foreground truncate flex-1">{summary}</span>
        {toolCall.lifecycle === 'running' ? (
          <Loader2 className="h-3.5 w-3.5 text-amber-500 animate-spin flex-shrink-0" />
        ) : toolCall.isError ? (
          <XCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />
        ) : (
          <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
        )}
        <span className="text-xs text-muted-foreground">
          {toolCall.timestamp.toLocaleTimeString("en-US", {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </span>
        {toolCall.duration !== undefined && (
          <span className="text-xs text-muted-foreground tabular-nums">
            {toolCall.duration.toFixed(1)}s
          </span>
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t p-3 space-y-3">
          {/* Error message if present */}
          {toolCall.isError && toolCall.errorMessage && (
            <div className="p-2 rounded bg-red-500/10 text-red-600 dark:text-red-400 text-xs">
              {toolCall.errorMessage}
            </div>
          )}

          {/* Edit tool: show diff view */}
          {hasOldNewStrings && (
            <EditDiffView
              filePath={String(toolCall.toolInput.file_path || "")}
              oldString={String(toolCall.toolInput.old_string)}
              newString={String(toolCall.toolInput.new_string)}
            />
          )}

          {/* Other tools: show full input */}
          {!hasOldNewStrings && (
            <ToolInputView input={toolCall.toolInput} toolName={toolCall.toolName} />
          )}
        </div>
      )}
    </div>
  );
}

// Edit Diff View

interface EditDiffViewProps {
  filePath: string;
  oldString: string;
  newString: string;
}

function EditDiffView({ filePath, oldString, newString }: EditDiffViewProps) {
  return (
    <div className="space-y-2">
      {/* File path */}
      {filePath && (
        <div className="flex items-center gap-2 text-xs">
          <Badge variant="outline">File</Badge>
          <code className="font-mono text-muted-foreground">{filePath}</code>
        </div>
      )}

      {/* Side by side diff */}
      <div className="grid grid-cols-2 gap-2">
        {/* Old string */}
        <div>
          <div className="text-xs font-medium text-red-600 dark:text-red-400 mb-1 flex items-center gap-1">
            <span className="w-4 h-4 rounded bg-red-500/20 flex items-center justify-center text-[10px]">
              -
            </span>
            old_string
          </div>
          <pre className="p-2 rounded bg-red-500/10 text-xs font-mono whitespace-pre-wrap break-words overflow-x-auto max-h-60 overflow-y-auto">
            {oldString || "(empty)"}
          </pre>
        </div>

        {/* New string */}
        <div>
          <div className="text-xs font-medium text-green-600 dark:text-green-400 mb-1 flex items-center gap-1">
            <span className="w-4 h-4 rounded bg-green-500/20 flex items-center justify-center text-[10px]">
              +
            </span>
            new_string
          </div>
          <pre className="p-2 rounded bg-green-500/10 text-xs font-mono whitespace-pre-wrap break-words overflow-x-auto max-h-60 overflow-y-auto">
            {newString || "(empty)"}
          </pre>
        </div>
      </div>
    </div>
  );
}

// Tool Input View (generic)

interface ToolInputViewProps {
  input: Record<string, unknown>;
  toolName: string;
}

function ToolInputView({ input, toolName }: ToolInputViewProps) {
  // Special rendering for specific tools
  if (toolName === "Bash" && input.command) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs">
          <Badge variant="outline">Command</Badge>
        </div>
        <pre className="p-2 rounded bg-muted text-xs font-mono whitespace-pre-wrap break-words">
          {String(input.command)}
        </pre>
        {typeof input.description === "string" && (
          <p className="text-xs text-muted-foreground">{input.description}</p>
        )}
      </div>
    );
  }

  if ((toolName === "Read" || toolName === "Write") && input.file_path) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs">
          <Badge variant="outline">File</Badge>
          <code className="font-mono text-muted-foreground">{String(input.file_path)}</code>
        </div>
        {typeof input.content === "string" && (
          <>
            <div className="text-xs font-medium text-muted-foreground">Content:</div>
            <pre className="p-2 rounded bg-muted text-xs font-mono whitespace-pre-wrap break-words max-h-40 overflow-y-auto">
              {input.content.slice(0, 1000)}
              {input.content.length > 1000 && "..."}
            </pre>
          </>
        )}
      </div>
    );
  }

  if ((toolName === "Glob" || toolName === "Grep") && input.pattern) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs">
          <Badge variant="outline">Pattern</Badge>
          <code className="font-mono">{String(input.pattern)}</code>
        </div>
        {typeof input.path === "string" && (
          <div className="flex items-center gap-2 text-xs">
            <Badge variant="outline">Path</Badge>
            <code className="font-mono text-muted-foreground">{input.path}</code>
          </div>
        )}
      </div>
    );
  }

  // Generic JSON view for other tools
  return (
    <div className="space-y-2">
      <div className="text-xs font-medium text-muted-foreground">Input:</div>
      <pre className="p-2 rounded bg-muted text-xs font-mono whitespace-pre-wrap break-words overflow-x-auto max-h-60 overflow-y-auto">
        {JSON.stringify(input, null, 2)}
      </pre>
    </div>
  );
}

// Helpers

function formatToolSummary(toolName: string, input: Record<string, unknown>): string {
  switch (toolName) {
    case "Read":
    case "Write":
    case "Edit":
      if (input.file_path) {
        return String(input.file_path);
      }
      break;
    case "Bash":
      if (input.command) {
        const cmd = String(input.command);
        return cmd.length > 60 ? cmd.slice(0, 60) + "..." : cmd;
      }
      break;
    case "Glob":
    case "Grep":
      if (input.pattern) {
        return `"${input.pattern}"`;
      }
      break;
  }

  // Generic fallback
  const keys = Object.keys(input);
  if (keys.length === 0) return "";
  return keys.slice(0, 2).join(", ");
}
