import {
  Circle,
  CheckCircle2,
  Loader2,
  Clock,
  AlertCircle,
  FileText,
  Layers,
  GitBranch,
  AlertTriangle,
} from "lucide-react";

export const STATUS_ORDER: Record<string, number> = {
  in_progress: 0,
  decomposed: 1,
  drafting: 2,
  completed: 3,
  failed: 4,
};

export const SESSION_STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-500 dark:bg-green-500",
  running: "bg-blue-500 dark:bg-blue-500",
  failed: "bg-red-500 dark:bg-red-500",
  paused: "bg-yellow-500 dark:bg-yellow-500",
};

export const FEATURE_STATUS_ICON: Record<string, typeof Circle> = {
  done: CheckCircle2,
  in_progress: Loader2,
  review: Clock,
  failed: AlertCircle,
  blocked: AlertCircle,
  planned: FileText,
  backlog: Circle,
};

export const FEATURE_STATUS_COLOR: Record<string, string> = {
  done: "text-green-500",
  in_progress: "text-blue-500",
  review: "text-yellow-500",
  failed: "text-red-500",
  blocked: "text-red-500",
  planned: "text-muted-foreground",
  backlog: "text-muted-foreground/50",
};

export const RISK_BADGE_CLASS: Record<string, string> = {
  low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  high: "bg-orange-50 text-orange-700 border-orange-200",
  critical: "bg-red-50 text-red-700 border-red-200",
};

export const SIGNAL_TYPE_ICON: Record<string, typeof Circle> = {
  file_modified: FileText,
  blocker: AlertCircle,
  discovery: Layers,
  api_changed: GitBranch,
  status_update: CheckCircle2,
  file_claim: FileText,
  judge_finding: AlertTriangle,
};

export const SIGNAL_TYPE_COLOR: Record<string, string> = {
  file_modified: "text-blue-500",
  blocker: "text-red-500",
  discovery: "text-purple-500",
  api_changed: "text-orange-500",
  status_update: "text-green-500",
  file_claim: "text-muted-foreground",
  judge_finding: "text-amber-500",
};
