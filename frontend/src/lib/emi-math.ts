/**
 * Client-side EMI math for instant slider responsiveness (no API round-trip).
 * EMI = P * r * (1+r)^n / ((1+r)^n - 1)
 */

export function calculateEMI(principal: number, annualRate: number, tenureMonths: number): number {
  if (principal <= 0 || tenureMonths <= 0) return 0;
  if (annualRate === 0) return principal / tenureMonths;

  const r = annualRate / 1200; // Monthly rate
  const n = tenureMonths;
  const factor = Math.pow(1 + r, n);
  return Math.round((principal * r * factor) / (factor - 1));
}

export function calculateTotalInterest(principal: number, annualRate: number, tenureMonths: number): number {
  const emi = calculateEMI(principal, annualRate, tenureMonths);
  return Math.round(emi * tenureMonths - principal);
}

export interface AmortizationEntry {
  month: number;
  emi: number;
  principal: number;
  interest: number;
  balance: number;
  cumulativeInterest: number;
}

export function generateAmortization(
  principal: number,
  annualRate: number,
  tenureMonths: number,
  monthlyPrepayment: number = 0,
): AmortizationEntry[] {
  if (principal <= 0 || tenureMonths <= 0) return [];

  const emi = calculateEMI(principal, annualRate, tenureMonths);
  const r = annualRate > 0 ? annualRate / 1200 : 0;
  let balance = principal;
  const schedule: AmortizationEntry[] = [];
  let cumulativeInterest = 0;

  for (let month = 1; month <= tenureMonths && balance > 0; month++) {
    const interest = Math.round(balance * r);
    let principalPortion = emi - interest;

    if (principalPortion > balance) principalPortion = balance;
    balance -= principalPortion;

    if (monthlyPrepayment > 0 && balance > 0) {
      const prepay = Math.min(monthlyPrepayment, balance);
      balance -= prepay;
      principalPortion += prepay;
    }

    cumulativeInterest += interest;
    balance = Math.max(0, balance);

    schedule.push({
      month,
      emi: principalPortion + interest,
      principal: principalPortion,
      interest,
      balance,
      cumulativeInterest,
    });

    if (balance <= 0) break;
  }

  return schedule;
}

export function calculateInterestSaved(
  principal: number,
  annualRate: number,
  tenureMonths: number,
  monthlyPrepayment: number,
): { interestSaved: number; monthsSaved: number } {
  const baselineInterest = calculateTotalInterest(principal, annualRate, tenureMonths);
  const schedule = generateAmortization(principal, annualRate, tenureMonths, monthlyPrepayment);
  const actualInterest = schedule.length > 0 ? schedule[schedule.length - 1].cumulativeInterest : 0;

  return {
    interestSaved: baselineInterest - actualInterest,
    monthsSaved: tenureMonths - schedule.length,
  };
}

export function reverseEMIRate(principal: number, emi: number, tenureMonths: number): number {
  let low = 0.01, high = 50;
  for (let i = 0; i < 100; i++) {
    const mid = (low + high) / 2;
    const calcEmi = calculateEMI(principal, mid, tenureMonths);
    if (Math.abs(calcEmi - emi) <= 1) return Math.round(mid * 100) / 100;
    if (calcEmi < emi) low = mid; else high = mid;
  }
  return Math.round(((low + high) / 2) * 100) / 100;
}

export function calculateAffordability(emi: number, annualRate: number, tenureMonths: number): number {
  if (emi <= 0 || tenureMonths <= 0) return 0;
  if (annualRate === 0) return emi * tenureMonths;
  const r = annualRate / 1200;
  const factor = Math.pow(1 + r, tenureMonths);
  return Math.round(emi * (factor - 1) / (r * factor));
}
