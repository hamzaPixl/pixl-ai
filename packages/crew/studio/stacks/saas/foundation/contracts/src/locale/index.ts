/**
 * Locale resolver for JSONB-based i18n fields.
 *
 * Resolves localized content from `{ en: "Hello", fr: "Bonjour" }` JSONB columns
 * based on the request's Accept-Language header or explicit locale parameter.
 */

export type LocaleMap = Record<string, string>;

export interface LocaleConfig {
  defaultLocale: string;
  supportedLocales: string[];
  fallbackChain?: string[];
}

const DEFAULT_LOCALE_CONFIG: LocaleConfig = {
  defaultLocale: "en",
  supportedLocales: ["en", "fr", "nl"],
  fallbackChain: ["en"],
};

/**
 * Resolve a localized value from a JSONB locale map.
 *
 * Resolution order:
 * 1. Exact locale match (e.g., "fr")
 * 2. Language prefix match (e.g., "fr-BE" → "fr")
 * 3. Fallback chain (e.g., "en")
 * 4. First available value
 * 5. Empty string
 */
export function resolveLocale(
  localeMap: LocaleMap | null | undefined,
  locale: string,
  config?: Partial<LocaleConfig>,
): string {
  if (!localeMap || Object.keys(localeMap).length === 0) {
    return "";
  }

  const cfg = { ...DEFAULT_LOCALE_CONFIG, ...config };

  // Exact match
  if (localeMap[locale] !== undefined) {
    return localeMap[locale];
  }

  // Language prefix match (e.g., "fr-BE" → "fr")
  const prefix = locale.split("-")[0];
  if (prefix !== locale && localeMap[prefix] !== undefined) {
    return localeMap[prefix];
  }

  // Fallback chain
  for (const fallback of cfg.fallbackChain ?? [cfg.defaultLocale]) {
    if (localeMap[fallback] !== undefined) {
      return localeMap[fallback];
    }
  }

  // First available
  const firstKey = Object.keys(localeMap)[0];
  return firstKey !== undefined ? localeMap[firstKey] : "";
}

/**
 * Resolve all localized fields on an object.
 *
 * Given `{ title: { en: "Hi", fr: "Salut" }, body: { en: "..." } }`
 * returns `{ title: "Salut", body: "..." }` for locale "fr".
 */
export function resolveLocalizedFields<T extends Record<string, unknown>>(
  obj: T,
  localizedKeys: (keyof T)[],
  locale: string,
  config?: Partial<LocaleConfig>,
): Record<string, unknown> {
  const result = { ...obj } as Record<string, unknown>;
  for (const key of localizedKeys) {
    const value = obj[key];
    if (value && typeof value === "object" && !Array.isArray(value)) {
      result[key as string] = resolveLocale(value as LocaleMap, locale, config);
    }
  }
  return result;
}

/**
 * Parse Accept-Language header into the best matching supported locale.
 *
 * Example: "fr-BE,fr;q=0.9,en;q=0.8" → "fr" (if supported)
 */
export function parseAcceptLanguage(
  header: string | undefined,
  config?: Partial<LocaleConfig>,
): string {
  const cfg = { ...DEFAULT_LOCALE_CONFIG, ...config };

  if (!header) return cfg.defaultLocale;

  const entries = header
    .split(",")
    .map((part) => {
      const [lang, ...params] = part.trim().split(";");
      const q = params.map((p) => p.trim()).find((p) => p.startsWith("q="));
      return {
        locale: lang.trim().toLowerCase(),
        quality: q ? Number.parseFloat(q.slice(2)) : 1.0,
      };
    })
    .sort((a, b) => b.quality - a.quality);

  for (const entry of entries) {
    if (cfg.supportedLocales.includes(entry.locale)) {
      return entry.locale;
    }
    const prefix = entry.locale.split("-")[0];
    if (cfg.supportedLocales.includes(prefix)) {
      return prefix;
    }
  }

  return cfg.defaultLocale;
}
