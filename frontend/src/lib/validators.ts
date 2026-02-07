import { z } from "zod";

export const loanSchema = z.object({
  bank_name: z.string().min(1, "Bank name is required").max(50),
  loan_type: z.enum(["home", "personal", "car", "education", "gold", "credit_card"]),
  principal_amount: z.number().positive("Must be greater than 0"),
  outstanding_principal: z.number().min(0),
  interest_rate: z.number().min(0).max(50, "Rate must be 0-50%"),
  interest_rate_type: z.enum(["floating", "fixed", "hybrid"]).default("floating"),
  tenure_months: z.number().int().positive().max(600),
  remaining_tenure_months: z.number().int().positive().max(600),
  emi_amount: z.number().positive(),
  emi_due_date: z.number().int().min(1).max(28).optional(),
  prepayment_penalty_pct: z.number().min(0).default(0),
  foreclosure_charges_pct: z.number().min(0).default(0),
  eligible_80c: z.boolean().default(false),
  eligible_24b: z.boolean().default(false),
  eligible_80e: z.boolean().default(false),
  eligible_80eea: z.boolean().default(false),
});

export const emiCalculatorSchema = z.object({
  principal: z.number().positive(),
  annual_rate: z.number().min(0).max(50),
  tenure_months: z.number().int().positive().max(600),
  monthly_prepayment: z.number().min(0).default(0),
});

export type LoanFormData = z.infer<typeof loanSchema>;
export type EMIFormData = z.infer<typeof emiCalculatorSchema>;
