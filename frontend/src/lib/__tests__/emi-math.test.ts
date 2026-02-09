import { describe, it, expect } from "vitest";
import {
  calculateEMI,
  calculateTotalInterest,
  generateAmortization,
  calculateInterestSaved,
  reverseEMIRate,
  calculateAffordability,
} from "../emi-math";

describe("calculateEMI", () => {
  it("computes SBI home loan benchmark: 50L at 8.5% for 20 years", () => {
    expect(calculateEMI(5_000_000, 8.5, 240)).toBe(43391);
  });

  it("returns principal/tenure when rate is zero", () => {
    expect(calculateEMI(1_200_000, 0, 120)).toBe(10000);
  });

  it("returns 0 when principal is zero", () => {
    expect(calculateEMI(0, 8.5, 240)).toBe(0);
  });

  it("returns 0 when tenure is zero", () => {
    expect(calculateEMI(5_000_000, 8.5, 0)).toBe(0);
  });
});

describe("calculateTotalInterest", () => {
  it("returns significant interest for a standard home loan", () => {
    const interest = calculateTotalInterest(5_000_000, 8.5, 240);
    expect(interest).toBeGreaterThan(0);
    // Total interest on 50L at 8.5% for 20y is roughly 54L
    expect(interest).toBeGreaterThan(5_000_000);
  });

  it("returns 0 when rate is zero", () => {
    expect(calculateTotalInterest(1_200_000, 0, 120)).toBe(0);
  });

  it("equals emi * tenure - principal", () => {
    const principal = 5_000_000;
    const rate = 8.5;
    const tenure = 240;
    const emi = calculateEMI(principal, rate, tenure);
    const totalInterest = calculateTotalInterest(principal, rate, tenure);
    expect(totalInterest).toBe(emi * tenure - principal);
  });
});

describe("generateAmortization", () => {
  it("produces a schedule with length equal to tenure (no prepayment)", () => {
    const schedule = generateAmortization(5_000_000, 8.5, 240);
    expect(schedule.length).toBe(240);
  });

  it("has higher interest than principal portion in the first month", () => {
    const schedule = generateAmortization(5_000_000, 8.5, 240);
    expect(schedule[0].interest).toBeGreaterThan(schedule[0].principal);
  });

  it("ends with a near-zero balance (rounding residual only)", () => {
    const schedule = generateAmortization(5_000_000, 8.5, 240);
    // Month-by-month Math.round on interest can leave a small residual;
    // it must be negligible relative to the original principal.
    expect(schedule[schedule.length - 1].balance).toBeLessThanOrEqual(500);
  });

  it("cumulative interest in last entry equals calculateTotalInterest", () => {
    const principal = 5_000_000;
    const rate = 8.5;
    const tenure = 240;
    const schedule = generateAmortization(principal, rate, tenure);
    const totalInterest = calculateTotalInterest(principal, rate, tenure);
    const cumulativeInterest = schedule[schedule.length - 1].cumulativeInterest;
    // Allow rounding tolerance of 1 rupee per month
    expect(Math.abs(cumulativeInterest - totalInterest)).toBeLessThanOrEqual(tenure);
  });

  it("shortens the schedule when a monthly prepayment is applied", () => {
    const schedule = generateAmortization(5_000_000, 8.5, 240, 5000);
    expect(schedule.length).toBeLessThan(240);
  });
});

describe("calculateInterestSaved", () => {
  it("reports positive savings with a monthly prepayment", () => {
    const { interestSaved, monthsSaved } = calculateInterestSaved(5_000_000, 8.5, 240, 5000);
    expect(interestSaved).toBeGreaterThan(0);
    expect(monthsSaved).toBeGreaterThan(0);
  });

  it("reports near-zero savings with no prepayment", () => {
    const { interestSaved, monthsSaved } = calculateInterestSaved(5_000_000, 8.5, 240, 0);
    // Rounding residual between calculateTotalInterest and amortization schedule;
    // the difference must be negligible (within a few hundred rupees).
    expect(Math.abs(interestSaved)).toBeLessThanOrEqual(500);
    expect(monthsSaved).toBe(0);
  });
});

describe("reverseEMIRate", () => {
  it("recovers the original rate from a known EMI (roundtrip)", () => {
    const emi = calculateEMI(5_000_000, 8.5, 240);
    const recoveredRate = reverseEMIRate(5_000_000, emi, 240);
    expect(recoveredRate).toBeCloseTo(8.5, 1);
  });

  it("converges within +/-0.1% of the expected rate", () => {
    const expectedRate = 10.0;
    const emi = calculateEMI(3_000_000, expectedRate, 180);
    const recoveredRate = reverseEMIRate(3_000_000, emi, 180);
    expect(Math.abs(recoveredRate - expectedRate)).toBeLessThanOrEqual(0.1);
  });
});

describe("calculateAffordability", () => {
  it("returns approximately the original principal (inverse of EMI)", () => {
    const affordable = calculateAffordability(43391, 8.5, 240);
    // Should be close to 50L; allow 0.1% tolerance
    expect(Math.abs(affordable - 5_000_000)).toBeLessThanOrEqual(5_000_000 * 0.001);
  });

  it("returns emi * tenure when rate is zero", () => {
    expect(calculateAffordability(10000, 0, 120)).toBe(1_200_000);
  });
});
