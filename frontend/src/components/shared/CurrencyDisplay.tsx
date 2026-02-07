import { formatINR, formatINRCompact } from "../../lib/format";

interface Props {
  amount: number;
  compact?: boolean;
  className?: string;
}

export function CurrencyDisplay({ amount, compact = false, className = "" }: Props) {
  const formatted = compact ? formatINRCompact(amount) : formatINR(amount);
  return <span className={className}>{formatted}</span>;
}
