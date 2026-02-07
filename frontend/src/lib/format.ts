/**
 * Indian number formatting utilities.
 * ₹1,00,000 (not ₹100,000)
 */

export function formatINR(amount: number): string {
  if (amount === 0) return "₹0";

  const isNegative = amount < 0;
  const absAmount = Math.abs(amount);

  // Indian numbering: last 3 digits, then groups of 2
  const parts = absAmount.toFixed(2).split(".");
  const integerPart = parts[0];
  const decimalPart = parts[1];

  let result: string;
  if (integerPart.length <= 3) {
    result = integerPart;
  } else {
    const lastThree = integerPart.slice(-3);
    const rest = integerPart.slice(0, -3);
    const formattedRest = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",");
    result = `${formattedRest},${lastThree}`;
  }

  // Remove trailing .00
  const formatted = decimalPart === "00" ? result : `${result}.${decimalPart}`;
  return `${isNegative ? "-" : ""}₹${formatted}`;
}

export function formatINRCompact(amount: number): string {
  const absAmount = Math.abs(amount);
  if (absAmount >= 10000000) return `₹${(amount / 10000000).toFixed(1)}Cr`;
  if (absAmount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (absAmount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
  return formatINR(amount);
}

export function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

export function formatMonths(months: number): string {
  const years = Math.floor(months / 12);
  const remaining = months % 12;
  if (years === 0) return `${remaining} month${remaining !== 1 ? "s" : ""}`;
  if (remaining === 0) return `${years} year${years !== 1 ? "s" : ""}`;
  return `${years}y ${remaining}m`;
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
