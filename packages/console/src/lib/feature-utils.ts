import type { Feature } from "@/types/api";
import { getFeatureTypeConfig } from "@/components/features/feature-type-config";

export const priorityOrder: Record<string, number> = {
  P0: 0,
  P1: 1,
  P2: 2,
  P3: 3,
};
export const ALL_PRIORITIES = ["P0", "P1", "P2", "P3"];

export type GroupBy = "none" | "status" | "epic" | "type";

export interface FeatureGroup {
  key: string;
  label: string;
  features: Feature[];
}

export function groupFeatures(
  features: Feature[],
  groupBy: GroupBy,
): FeatureGroup[] {
  if (groupBy === "none") {
    return [{ key: "__all", label: "", features }];
  }

  const map = new Map<string, Feature[]>();
  const keyLabels = new Map<string, string>();

  for (const f of features) {
    let key: string;
    let label: string;
    switch (groupBy) {
      case "status":
        key = f.status;
        label = f.status.replace(/_/g, " ").toUpperCase();
        break;
      case "epic":
        key = f.epic_id ?? "__none";
        label = f.epic_id ?? "No Epic";
        break;
      case "type":
        key = f.type ?? "feature";
        label = getFeatureTypeConfig(f.type).label;
        break;
    }
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(f);
    keyLabels.set(key, label);
  }

  return Array.from(map.entries()).map(([key, features]) => ({
    key,
    label: keyLabels.get(key) ?? key,
    features,
  }));
}
