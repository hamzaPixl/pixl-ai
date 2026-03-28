/**
 * Utility functions for shadcn/ui components.
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format AI model names for display in the UI.
 * Extracts provider and short model name, maps technical names to user-friendly names.
 */
export function formatModelName(modelName: string | null | undefined): string | null {
  if (!modelName) {
    return null;
  }

  const [provider, model] = modelName.includes('/')
    ? modelName.split('/')
    : [null, modelName];

  // Clean up the model name
  let displayModel = model;

  if (displayModel.includes('claude-opus')) {
    displayModel = 'Opus';
  } else if (displayModel.includes('claude-sonnet')) {
    displayModel = 'Sonnet';
  } else if (displayModel.includes('claude-haiku')) {
    displayModel = 'Haiku';
  } else if (displayModel.includes('gpt-5.2-codex')) {
    displayModel = 'Codex';
  } else if (displayModel.includes('gpt-4')) {
    displayModel = 'GPT-4';
  } else if (displayModel.includes('gpt-3.5')) {
    displayModel = 'GPT-3.5';
  } else {
    // For unknown models, take the part before the first dash or the full name
    const parts = displayModel.split('-');
    displayModel = parts.length > 1 ? parts[0] : displayModel;
    // Capitalize first letter
    displayModel = displayModel.charAt(0).toUpperCase() + displayModel.slice(1);
  }

  if (provider && provider !== 'anthropic') {
    displayModel = `${provider}/${displayModel}`;
  }

  return displayModel;
}

/**
 * Get the appropriate badge color for different model tiers.
 */
export function getModelBadgeColor(modelName: string | null | undefined): string {
  if (!modelName) {
    return "bg-gray-100 text-gray-700";
  }

  const model = modelName.toLowerCase();

  if (model.includes('opus')) {
    return "bg-purple-100 text-purple-700";
  } else if (model.includes('sonnet')) {
    return "bg-blue-100 text-blue-700";
  } else if (model.includes('haiku')) {
    return "bg-green-100 text-green-700";
  } else if (model.includes('codex')) {
    return "bg-orange-100 text-orange-700";
  } else {
    return "bg-gray-100 text-gray-700";
  }
}

/**
 * Cost per 1K tokens (input+output blended estimate) by model family.
 * These are rough estimates for display only.
 */
const MODEL_COST_PER_1K: Record<string, number> = {
  opus: 0.075,
  sonnet: 0.015,
  haiku: 0.005,
  codex: 0.01,
  'gpt-4': 0.03,
  'gpt-3.5': 0.002,
};

function getModelFamily(model: string): string {
  const m = model.toLowerCase();
  if (m.includes('opus')) return 'opus';
  if (m.includes('sonnet')) return 'sonnet';
  if (m.includes('haiku')) return 'haiku';
  if (m.includes('codex')) return 'codex';
  if (m.includes('gpt-4')) return 'gpt-4';
  if (m.includes('gpt-3.5')) return 'gpt-3.5';
  return 'sonnet';
}

export function estimateTokenCost(model: string, totalTokens: number): string {
  const family = getModelFamily(model);
  const costPer1K = MODEL_COST_PER_1K[family] ?? 0.015;
  const cost = (totalTokens / 1000) * costPer1K;
  if (cost < 0.01) return '< $0.01';
  return `$${cost.toFixed(2)}`;
}

export function formatTokenCount(tokens: number): string {
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
  return String(tokens);
}
