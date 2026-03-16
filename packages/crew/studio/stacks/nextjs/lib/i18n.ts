import { fr } from "@/lib/translations/fr";
import { en } from "@/lib/translations/en";
import { nl } from "@/lib/translations/nl";

const translations: Record<string, Record<string, unknown>> = { fr, en, nl };

function getNestedValue(obj: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

export function t(locale: string, key: string): string {
  const val = getNestedValue(translations[locale], key);
  if (typeof val === "string") return val;
  const fallback = getNestedValue(translations.fr, key);
  if (typeof fallback === "string") return fallback;
  return key;
}

export function tArray(locale: string, key: string): string[] {
  const val = getNestedValue(translations[locale], key);
  if (Array.isArray(val)) return val as string[];
  const fallback = getNestedValue(translations.fr, key);
  if (Array.isArray(fallback)) return fallback as string[];
  return [];
}

export function tRaw<T = unknown>(locale: string, key: string): T | undefined {
  const val = getNestedValue(translations[locale], key);
  if (val !== undefined) return val as T;
  const fallback = getNestedValue(translations.fr, key);
  return fallback as T | undefined;
}
