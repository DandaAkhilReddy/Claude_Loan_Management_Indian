import { formatCurrency, formatCurrencyCompact } from "../../lib/format";
import { useCountryConfig } from "../../hooks/useCountryConfig";

interface Props {
  amount: number;
  compact?: boolean;
  className?: string;
}

export function CurrencyDisplay({ amount, compact = false, className = "" }: Props) {
  const config = useCountryConfig();
  const formatted = compact
    ? formatCurrencyCompact(amount, config.code)
    : formatCurrency(amount, config.code);
  return <span className={className}>{formatted}</span>;
}
