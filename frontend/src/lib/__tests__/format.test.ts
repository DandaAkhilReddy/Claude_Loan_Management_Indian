import { describe, it, expect } from "vitest";
import { formatINR, formatINRCompact, formatPercent, formatMonths, formatDate } from "../format";

describe("formatINR", () => {
  it("formats zero", () => {
    expect(formatINR(0)).toBe("₹0");
  });

  it("formats small amounts without Indian grouping", () => {
    expect(formatINR(500)).toBe("₹500");
  });

  it("formats amounts with Indian grouping (last 3, then groups of 2)", () => {
    expect(formatINR(100000)).toBe("₹1,00,000");
  });

  it("formats 50 lakhs correctly", () => {
    expect(formatINR(5000000)).toBe("₹50,00,000");
  });

  it("formats 1 crore correctly", () => {
    expect(formatINR(10000000)).toBe("₹1,00,00,000");
  });

  it("formats with paisa (decimal)", () => {
    expect(formatINR(43391.50)).toBe("₹43,391.50");
  });

  it("strips trailing .00", () => {
    expect(formatINR(43391.00)).toBe("₹43,391");
  });

  it("formats negative amounts", () => {
    expect(formatINR(-5000)).toBe("-₹5,000");
  });
});

describe("formatINRCompact", () => {
  it("formats crores", () => {
    expect(formatINRCompact(10000000)).toBe("₹1.0Cr");
  });

  it("formats lakhs", () => {
    expect(formatINRCompact(500000)).toBe("₹5.0L");
  });

  it("formats thousands", () => {
    expect(formatINRCompact(5000)).toBe("₹5.0K");
  });

  it("falls back to formatINR for small amounts", () => {
    expect(formatINRCompact(500)).toBe("₹500");
  });
});

describe("formatPercent", () => {
  it("formats percentage with 2 decimals", () => {
    expect(formatPercent(8.5)).toBe("8.50%");
  });

  it("formats zero percent", () => {
    expect(formatPercent(0)).toBe("0.00%");
  });
});

describe("formatMonths", () => {
  it("formats months only", () => {
    expect(formatMonths(6)).toBe("6 months");
  });

  it("formats 1 month (singular)", () => {
    expect(formatMonths(1)).toBe("1 month");
  });

  it("formats years only", () => {
    expect(formatMonths(24)).toBe("2 years");
  });

  it("formats 1 year (singular)", () => {
    expect(formatMonths(12)).toBe("1 year");
  });

  it("formats mixed years and months", () => {
    expect(formatMonths(30)).toBe("2y 6m");
  });
});

describe("formatDate", () => {
  it("formats a date string", () => {
    const result = formatDate("2025-01-15");
    expect(result).toContain("Jan");
    expect(result).toContain("2025");
  });
});
