import { describe, it, expect } from "vitest";
import { loanSchema, emiCalculatorSchema } from "../validators";

const validLoan = {
  bank_name: "SBI",
  loan_type: "home" as const,
  principal_amount: 5000000,
  outstanding_principal: 4500000,
  interest_rate: 8.5,
  tenure_months: 240,
  remaining_tenure_months: 220,
  emi_amount: 43391,
};

describe("loanSchema", () => {
  it("valid full object passes", () => {
    const result = loanSchema.parse(validLoan);
    expect(result).toEqual(
      expect.objectContaining({
        bank_name: "SBI",
        loan_type: "home",
        principal_amount: 5000000,
        outstanding_principal: 4500000,
        interest_rate: 8.5,
        tenure_months: 240,
        remaining_tenure_months: 220,
        emi_amount: 43391,
      })
    );
  });

  it("missing bank_name fails", () => {
    expect(() =>
      loanSchema.parse({ ...validLoan, bank_name: "" })
    ).toThrow();
  });

  it("negative principal fails", () => {
    expect(() =>
      loanSchema.parse({ ...validLoan, principal_amount: -1000 })
    ).toThrow();
  });

  it("interest rate above 50 fails", () => {
    expect(() =>
      loanSchema.parse({ ...validLoan, interest_rate: 55 })
    ).toThrow();
  });

  it("tenure above 600 fails", () => {
    expect(() =>
      loanSchema.parse({ ...validLoan, tenure_months: 700 })
    ).toThrow();
  });

  it("emi_due_date above 28 fails", () => {
    expect(() =>
      loanSchema.parse({ ...validLoan, emi_due_date: 35 })
    ).toThrow();
  });

  it("default values applied", () => {
    const result = loanSchema.parse(validLoan);
    expect(result.interest_rate_type).toBe("floating");
    expect(result.eligible_80c).toBe(false);
    expect(result.eligible_24b).toBe(false);
    expect(result.eligible_80e).toBe(false);
    expect(result.eligible_80eea).toBe(false);
    expect(result.prepayment_penalty_pct).toBe(0);
    expect(result.foreclosure_charges_pct).toBe(0);
  });
});

describe("emiCalculatorSchema", () => {
  it("valid object passes", () => {
    const result = emiCalculatorSchema.parse({
      principal: 5000000,
      annual_rate: 8.5,
      tenure_months: 240,
    });
    expect(result).toEqual(
      expect.objectContaining({
        principal: 5000000,
        annual_rate: 8.5,
        tenure_months: 240,
      })
    );
  });

  it("negative prepayment fails", () => {
    expect(() =>
      emiCalculatorSchema.parse({
        principal: 5000000,
        annual_rate: 8.5,
        tenure_months: 240,
        monthly_prepayment: -100,
      })
    ).toThrow();
  });

  it("default prepayment is 0", () => {
    const result = emiCalculatorSchema.parse({
      principal: 5000000,
      annual_rate: 8.5,
      tenure_months: 240,
    });
    expect(result.monthly_prepayment).toBe(0);
  });
});
