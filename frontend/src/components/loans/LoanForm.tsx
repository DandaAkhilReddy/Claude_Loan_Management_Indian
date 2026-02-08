import { useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { useCountryConfig } from "../../hooks/useCountryConfig";

interface Props {
  onSubmit: (data: any) => void;
  onClose: () => void;
  isLoading?: boolean;
  initialData?: any;
}

export function LoanForm({ onSubmit, onClose, isLoading, initialData }: Props) {
  const { t } = useTranslation();
  const config = useCountryConfig();

  const [form, setForm] = useState({
    bank_name: initialData?.bank_name || "",
    loan_type: initialData?.loan_type || "home",
    principal_amount: initialData?.principal_amount || "",
    outstanding_principal: initialData?.outstanding_principal || "",
    interest_rate: initialData?.interest_rate || "",
    interest_rate_type: initialData?.interest_rate_type || "floating",
    tenure_months: initialData?.tenure_months || "",
    remaining_tenure_months: initialData?.remaining_tenure_months || "",
    emi_amount: initialData?.emi_amount || "",
    emi_due_date: initialData?.emi_due_date || "",
    // India tax sections
    eligible_80c: initialData?.eligible_80c || false,
    eligible_24b: initialData?.eligible_24b || false,
    eligible_80e: initialData?.eligible_80e || false,
    eligible_80eea: initialData?.eligible_80eea || false,
    // US deductions
    eligible_mortgage_deduction: initialData?.eligible_mortgage_deduction || false,
    eligible_student_loan_deduction: initialData?.eligible_student_loan_deduction || false,
  });

  const handleChange = (field: string, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      ...form,
      principal_amount: Number(form.principal_amount),
      outstanding_principal: Number(form.outstanding_principal),
      interest_rate: Number(form.interest_rate),
      tenure_months: Number(form.tenure_months),
      remaining_tenure_months: Number(form.remaining_tenure_months),
      emi_amount: Number(form.emi_amount),
      emi_due_date: form.emi_due_date ? Number(form.emi_due_date) : null,
      prepayment_penalty_pct: 0,
      foreclosure_charges_pct: 0,
    });
  };

  const sym = config.currencySymbol;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold">{t("loanForm.title")}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("loanForm.selectBank")}</label>
              <select
                value={form.bank_name}
                onChange={(e) => handleChange("bank_name", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                required
              >
                <option value="">{t("loanForm.selectBank")}</option>
                {config.banks.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("loans.type")}</label>
              <select
                value={form.loan_type}
                onChange={(e) => handleChange("loan_type", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm capitalize"
              >
                {config.loanTypes.map((lt) => <option key={lt} value={lt}>{lt.replace("_", " ")}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("loanForm.originalAmount")} ({sym})</label>
              <input type="number" value={form.principal_amount} onChange={(e) => handleChange("principal_amount", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" required min="1" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("loanForm.outstandingAmount")} ({sym})</label>
              <input type="number" value={form.outstanding_principal} onChange={(e) => handleChange("outstanding_principal", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" required min="0" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("loanForm.interestRate")} (%)</label>
              <input type="number" step="0.01" value={form.interest_rate} onChange={(e) => handleChange("interest_rate", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" required min="0" max="50" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("loanForm.rateType")}</label>
              <select value={form.interest_rate_type} onChange={(e) => handleChange("interest_rate_type", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                <option value="floating">{t("loanForm.floating")}</option>
                <option value="fixed">{t("loanForm.fixed")}</option>
                <option value="hybrid">{t("loanForm.hybrid")}</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("loanForm.totalTenure")}</label>
              <input type="number" value={form.tenure_months} onChange={(e) => handleChange("tenure_months", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" required min="1" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("loanForm.remainingTenure")}</label>
              <input type="number" value={form.remaining_tenure_months} onChange={(e) => handleChange("remaining_tenure_months", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" required min="1" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("loanForm.emiAmount")} ({sym})</label>
              <input type="number" value={form.emi_amount} onChange={(e) => handleChange("emi_amount", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" required min="1" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("loanForm.emiDueDate")}</label>
              <input type="number" value={form.emi_due_date} onChange={(e) => handleChange("emi_due_date", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" min="1" max="28" placeholder={t("loanForm.dayHint")} />
            </div>
          </div>

          {/* India Tax Deductions */}
          {config.hasTaxSections && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t("loanForm.taxDeductions")}</label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { key: "eligible_80c", label: t("loanForm.section80c") },
                  { key: "eligible_24b", label: t("loanForm.section24b") },
                  { key: "eligible_80e", label: t("loanForm.section80e") },
                  { key: "eligible_80eea", label: t("loanForm.section80eea") },
                ].map(({ key, label }) => (
                  <label key={key} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={(form as any)[key]}
                      onChange={(e) => handleChange(key, e.target.checked)}
                      className="rounded border-gray-300 text-blue-600"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* US Tax Deductions */}
          {config.hasFilingStatus && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t("loanForm.taxDeductions")}</label>
              <div className="grid grid-cols-1 gap-2">
                {[
                  { key: "eligible_mortgage_deduction", label: t("loanForm.mortgageDeduction") },
                  { key: "eligible_student_loan_deduction", label: t("loanForm.studentLoanDeduction") },
                ].map(({ key, label }) => (
                  <label key={key} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={(form as any)[key]}
                      onChange={(e) => handleChange(key, e.target.checked)}
                      className="rounded border-gray-300 text-blue-600"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? t("loanForm.saving") : t("loanForm.saveLoan")}
          </button>
        </form>
      </div>
    </div>
  );
}
