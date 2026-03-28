import {
  FileCode,
  TestTube,
  ScrollText,
  ClipboardCheck,
  BookOpen,
  FileText,
  CheckCircle2,
  XCircle,
  CircleDot,
  Circle,
  AlertTriangle,
} from "lucide-react";
import { createElement } from "react";

export const statusColors: Record<string, string> = {
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

export const artifactTypeIcon: Record<string, React.ReactNode> = {
  code: createElement(FileCode, { className: "h-4 w-4 text-blue-500" }),
  test: createElement(TestTube, { className: "h-4 w-4 text-green-500" }),
  plan: createElement(ScrollText, { className: "h-4 w-4 text-amber-500" }),
  review: createElement(ClipboardCheck, {
    className: "h-4 w-4 text-purple-500",
  }),
  document: createElement(BookOpen, { className: "h-4 w-4 text-cyan-500" }),
  context: createElement(FileText, {
    className: "h-4 w-4 text-muted-foreground",
  }),
};

export const artifactTypeBg: Record<string, string> = {
  code: "border-blue-200 dark:border-blue-800",
  test: "border-green-200 dark:border-green-800",
  plan: "border-amber-200 dark:border-amber-800",
  review: "border-purple-200 dark:border-purple-800",
  document: "border-cyan-200 dark:border-cyan-800",
};

export const timelineStatusIcon: Record<string, React.ReactNode> = {
  done: createElement(CheckCircle2, { className: "h-4 w-4 text-green-500" }),
  completed: createElement(CheckCircle2, {
    className: "h-4 w-4 text-green-500",
  }),
  failed: createElement(XCircle, { className: "h-4 w-4 text-red-500" }),
  blocked: createElement(AlertTriangle, { className: "h-4 w-4 text-red-400" }),
  in_progress: createElement(CircleDot, {
    className: "h-4 w-4 text-yellow-500",
  }),
  review: createElement(CircleDot, { className: "h-4 w-4 text-purple-500" }),
  planned: createElement(Circle, { className: "h-4 w-4 text-blue-400" }),
  backlog: createElement(Circle, {
    className: "h-4 w-4 text-muted-foreground",
  }),
};

export const timelineStatusColor: Record<string, string> = {
  done: "border-green-300 dark:border-green-700",
  completed: "border-green-300 dark:border-green-700",
  failed: "border-red-300 dark:border-red-700",
  blocked: "border-red-200 dark:border-red-800",
  in_progress: "border-yellow-300 dark:border-yellow-700",
  review: "border-purple-300 dark:border-purple-700",
  planned: "border-blue-200 dark:border-blue-800",
  backlog: "border-muted",
};
