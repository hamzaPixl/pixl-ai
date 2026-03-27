export const statusColors: Record<string, string> = {
  plan_draft: "bg-muted text-muted-foreground",
  plan_ready: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  running:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
  paused:
    "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
  completed:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  cancelled: "bg-muted text-muted-foreground",
};
