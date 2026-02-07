export interface Loan {
  id: string;
  user_id: string;
  bank_name: string;
  loan_type: "home" | "personal" | "car" | "education" | "gold" | "credit_card";
  principal_amount: number;
  outstanding_principal: number;
  interest_rate: number;
  interest_rate_type: "floating" | "fixed" | "hybrid";
  tenure_months: number;
  remaining_tenure_months: number;
  emi_amount: number;
  emi_due_date: number | null;
  prepayment_penalty_pct: number;
  foreclosure_charges_pct: number;
  eligible_80c: boolean;
  eligible_24b: boolean;
  eligible_80e: boolean;
  eligible_80eea: boolean;
  disbursement_date: string | null;
  status: "active" | "closed";
  source: "manual" | "scan" | "account_aggregator";
  source_scan_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AmortizationEntry {
  month: number;
  emi: number;
  principal: number;
  interest: number;
  balance: number;
  prepayment: number;
  cumulative_interest: number;
}

export interface LoanResult {
  loan_id: string;
  bank_name: string;
  loan_type: string;
  original_balance: number;
  payoff_month: number;
  months_saved: number;
}

export interface StrategyResult {
  strategy_name: string;
  strategy_description: string;
  total_interest_paid: number;
  total_months: number;
  interest_saved_vs_baseline: number;
  months_saved_vs_baseline: number;
  payoff_order: string[];
  loan_results: LoanResult[];
  debt_free_date_months: number;
}

export interface OptimizationResult {
  baseline_total_interest: number;
  baseline_total_months: number;
  strategies: StrategyResult[];
  recommended_strategy: string;
}

export interface ScanJob {
  job_id: string;
  status: "uploaded" | "processing" | "completed" | "review_needed" | "failed";
  extracted_fields: ExtractedField[] | null;
  error_message: string | null;
  processing_time_ms: number | null;
  created_at: string;
}

export interface ExtractedField {
  field_name: string;
  value: string;
  confidence: number;
}

export interface EMIResult {
  emi: number;
  total_interest: number;
  total_payment: number;
  interest_saved: number;
  months_saved: number;
}

export interface TaxImpact {
  old_regime_tax: number;
  new_regime_tax: number;
  recommended: string;
  savings: number;
  explanation: string;
  deductions: Record<string, number>;
}
