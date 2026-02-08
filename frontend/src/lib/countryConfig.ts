import type { CountryCode } from "../store/countryStore";

export interface CompactUnit {
  threshold: number;
  suffix: string;
  divisor: number;
}

export interface SliderRange {
  min: number;
  max: number;
  step: number;
}

export interface CountryConfig {
  code: CountryCode;
  currencyCode: string;
  currencySymbol: string;
  currencyLocale: string;
  dateLocale: string;
  banks: string[];
  loanTypes: string[];
  hasTaxSections: boolean;
  hasFilingStatus: boolean;
  compactUnits: CompactUnit[];
  sliderRanges: {
    principal: SliderRange;
    dailySaving: SliderRange;
    monthlyExtra: SliderRange;
    lumpSumDefault: number;
  };
  budgetModeKey: string;
  privacyLawKey: string;
}

export const COUNTRY_CONFIGS: Record<CountryCode, CountryConfig> = {
  IN: {
    code: "IN",
    currencyCode: "INR",
    currencySymbol: "₹",
    currencyLocale: "en-IN",
    dateLocale: "en-IN",
    banks: [
      "SBI", "HDFC", "ICICI", "AXIS", "PNB", "BOB",
      "KOTAK", "CANARA", "UNION", "BAJAJ", "LIC_HFL", "Other",
    ],
    loanTypes: ["home", "personal", "car", "education", "gold", "credit_card"],
    hasTaxSections: true,
    hasFilingStatus: false,
    compactUnits: [
      { threshold: 1e7, suffix: "Cr", divisor: 1e7 },
      { threshold: 1e5, suffix: "L", divisor: 1e5 },
      { threshold: 1e3, suffix: "K", divisor: 1e3 },
    ],
    sliderRanges: {
      principal: { min: 100000, max: 50000000, step: 100000 },
      dailySaving: { min: 10, max: 1000, step: 10 },
      monthlyExtra: { min: 0, max: 50000, step: 500 },
      lumpSumDefault: 50000,
    },
    budgetModeKey: "optimizer.budget.gullakMode",
    privacyLawKey: "settings.dpdpAct",
  },
  US: {
    code: "US",
    currencyCode: "USD",
    currencySymbol: "$",
    currencyLocale: "en-US",
    dateLocale: "en-US",
    banks: [
      "Chase", "Bank of America", "Wells Fargo", "Citi", "US Bank",
      "PNC", "Capital One", "TD Bank", "Ally", "SoFi", "Other",
    ],
    loanTypes: ["home", "personal", "car", "education", "business", "credit_card"],
    hasTaxSections: false,
    hasFilingStatus: true,
    compactUnits: [
      { threshold: 1e9, suffix: "B", divisor: 1e9 },
      { threshold: 1e6, suffix: "M", divisor: 1e6 },
      { threshold: 1e3, suffix: "K", divisor: 1e3 },
    ],
    sliderRanges: {
      principal: { min: 1000, max: 5000000, step: 1000 },
      dailySaving: { min: 1, max: 100, step: 1 },
      monthlyExtra: { min: 0, max: 5000, step: 50 },
      lumpSumDefault: 5000,
    },
    budgetModeKey: "optimizer.budget.piggyBankMode",
    privacyLawKey: "settings.ccpa",
  },
};
