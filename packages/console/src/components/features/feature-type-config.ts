/**
 * Feature type configuration: icon, color, and label mapping.
 * Used by list cards, kanban cards, and table rows.
 */

import {
  Sparkles,
  Bug,
  RefreshCw,
  FileText,
  Wrench,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import type { FeatureType } from '@/types/api';

export interface FeatureTypeConfig {
  icon: LucideIcon;
  color: string;       // Tailwind text color class
  bg: string;          // Tailwind bg color class for icon container
  label: string;
}

export const FEATURE_TYPE_CONFIG: Record<FeatureType, FeatureTypeConfig> = {
  feature: {
    icon: Sparkles,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
    label: 'Feature',
  },
  bug: {
    icon: Bug,
    color: 'text-red-500',
    bg: 'bg-red-500/10',
    label: 'Bug',
  },
  refactor: {
    icon: RefreshCw,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10',
    label: 'Refactor',
  },
  docs: {
    icon: FileText,
    color: 'text-green-500',
    bg: 'bg-green-500/10',
    label: 'Docs',
  },
  chore: {
    icon: Wrench,
    color: 'text-gray-500',
    bg: 'bg-gray-500/10',
    label: 'Chore',
  },
  execution: {
    icon: Zap,
    color: 'text-purple-500',
    bg: 'bg-purple-500/10',
    label: 'Execution',
  },
};

export function getFeatureTypeConfig(type: FeatureType | undefined): FeatureTypeConfig {
  return FEATURE_TYPE_CONFIG[type ?? 'feature'] ?? FEATURE_TYPE_CONFIG.feature;
}
