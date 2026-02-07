import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

/**
 * Verify all 3 locale files have consistent keys.
 */
function loadLocale(lang: string): Record<string, unknown> {
  const filePath = path.resolve(__dirname, `../../locales/${lang}.json`);
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

function flattenKeys(obj: Record<string, unknown>, prefix = ""): string[] {
  const keys: string[] = [];
  for (const [k, v] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${k}` : k;
    if (typeof v === "object" && v !== null && !Array.isArray(v)) {
      keys.push(...flattenKeys(v as Record<string, unknown>, fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys.sort();
}

describe("i18n locale consistency", () => {
  const en = loadLocale("en");
  const hi = loadLocale("hi");
  const te = loadLocale("te");

  const enKeys = flattenKeys(en);
  const hiKeys = flattenKeys(hi);
  const teKeys = flattenKeys(te);

  it("English locale has keys", () => {
    expect(enKeys.length).toBeGreaterThan(0);
  });

  it("Hindi has all English keys", () => {
    const missing = enKeys.filter((k) => !hiKeys.includes(k));
    expect(missing).toEqual([]);
  });

  it("Telugu has all English keys", () => {
    const missing = enKeys.filter((k) => !teKeys.includes(k));
    expect(missing).toEqual([]);
  });

  it("Hindi has no extra keys beyond English", () => {
    const extra = hiKeys.filter((k) => !enKeys.includes(k));
    expect(extra).toEqual([]);
  });

  it("Telugu has no extra keys beyond English", () => {
    const extra = teKeys.filter((k) => !enKeys.includes(k));
    expect(extra).toEqual([]);
  });

  it("interpolation variables match across locales", () => {
    const interpolationRegex = /\{\{(\w+)\}\}/g;

    for (const key of enKeys) {
      const enVal = getNestedValue(en, key);
      const hiVal = getNestedValue(hi, key);
      const teVal = getNestedValue(te, key);

      if (typeof enVal !== "string") continue;

      const enVars = [...enVal.matchAll(interpolationRegex)].map((m) => m[1]).sort();
      if (enVars.length === 0) continue;

      if (typeof hiVal === "string") {
        const hiVars = [...hiVal.matchAll(interpolationRegex)].map((m) => m[1]).sort();
        expect(hiVars, `Hindi key "${key}" should have vars ${enVars}`).toEqual(enVars);
      }

      if (typeof teVal === "string") {
        const teVars = [...teVal.matchAll(interpolationRegex)].map((m) => m[1]).sort();
        expect(teVars, `Telugu key "${key}" should have vars ${enVars}`).toEqual(enVars);
      }
    }
  });
});

function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}
