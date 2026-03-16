"use client";

import { useLanguage, type Locale } from "@/lib/language-context";
import { fr } from "@/lib/translations/fr";
import { nl } from "@/lib/translations/nl";
import { en } from "@/lib/translations/en";

const translations: Record<Locale, Record<string, unknown>> = { fr, nl, en };

function getNestedValue(obj: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

export function useTranslate() {
  const { currentLanguage } = useLanguage();

  function t(key: string): string {
    const val = getNestedValue(translations[currentLanguage], key);
    if (typeof val === "string") return val;
    // Fallback to FR
    const fallback = getNestedValue(translations.fr, key);
    if (typeof fallback === "string") return fallback;
    return key;
  }

  function tArray(key: string): string[] {
    const val = getNestedValue(translations[currentLanguage], key);
    if (Array.isArray(val)) return val as string[];
    const fallback = getNestedValue(translations.fr, key);
    if (Array.isArray(fallback)) return fallback as string[];
    return [];
  }

  function tRaw<T = unknown>(key: string): T {
    const val = getNestedValue(translations[currentLanguage], key);
    if (val !== undefined) return val as T;
    return getNestedValue(translations.fr, key) as T;
  }

  return { t, tArray, tRaw, currentLanguage };
}
