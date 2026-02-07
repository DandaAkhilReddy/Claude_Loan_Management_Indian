import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import api from "../lib/api";
import { formatINR, formatMonths } from "../lib/format";
import { LoadingSpinner } from "../components/shared/LoadingSpinner";
import type { Loan, AmortizationEntry } from "../types";

export function LoanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const { data: loan, isLoading } = useQuery<Loan>({
    queryKey: ["loan", id],
    queryFn: () => api.get(`/api/loans/${id}`).then((r) => r.data),
  });

  const { data: amortization } = useQuery<{ schedule: AmortizationEntry[]; total_interest: number }>({
    queryKey: ["amortization", id],
    queryFn: () => api.get(`/api/loans/${id}/amortization`).then((r) => r.data),
    enabled: !!id,
  });

  if (isLoading) return <LoadingSpinner size="lg" />;
  if (!loan) return <div className="text-center py-8 text-gray-500">{t("loanDetail.notFound")}</div>;

  const paidPercent = Math.round((1 - loan.outstanding_principal / loan.principal_amount) * 100);

  return (
    <div className="space-y-6">
      <button onClick={() => navigate("/loans")} className="flex items-center gap-2 text-gray-600 hover:text-gray-900 text-sm">
        <ArrowLeft className="w-4 h-4" /> {t("loanDetail.backToLoans")}
      </button>

      {/* Loan Summary */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{loan.bank_name}</h1>
            <p className="text-sm text-gray-500 capitalize">{loan.loan_type} loan — {loan.interest_rate_type} rate</p>
          </div>
          <span className="text-2xl font-bold text-blue-600">{loan.interest_rate}%</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-400">{t("loanDetail.originalAmount")}</p>
            <p className="font-semibold">{formatINR(loan.principal_amount)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">{t("loanDetail.outstanding")}</p>
            <p className="font-semibold">{formatINR(loan.outstanding_principal)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">{t("loanDetail.monthlyEmi")}</p>
            <p className="font-semibold">{formatINR(loan.emi_amount)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">{t("loanDetail.remaining")}</p>
            <p className="font-semibold">{formatMonths(loan.remaining_tenure_months)}</p>
          </div>
        </div>

        <div className="mt-4">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>{t("loanDetail.paidPercent", { percent: paidPercent })}</span>
            <span>{t("loanDetail.amountRemaining", { amount: formatINR(loan.outstanding_principal) })}</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.max(2, paidPercent)}%` }} />
          </div>
        </div>
      </div>

      {/* Amortization Table */}
      {amortization?.schedule && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">{t("loanDetail.amortizationSchedule")}</h2>
            <p className="text-sm text-gray-500">{t("loanDetail.totalInterest")}: {formatINR(amortization.total_interest)}</p>
          </div>
          <div className="overflow-x-auto max-h-96">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="text-left px-4 py-2 text-gray-500 font-medium">{t("loanDetail.month")}</th>
                  <th className="text-right px-4 py-2 text-gray-500 font-medium">{t("loanDetail.emi")}</th>
                  <th className="text-right px-4 py-2 text-gray-500 font-medium">{t("loanDetail.principal")}</th>
                  <th className="text-right px-4 py-2 text-gray-500 font-medium">{t("loanDetail.interest")}</th>
                  <th className="text-right px-4 py-2 text-gray-500 font-medium">{t("loanDetail.balance")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {amortization.schedule.map((entry) => (
                  <tr key={entry.month}>
                    <td className="px-4 py-2">{entry.month}</td>
                    <td className="px-4 py-2 text-right">{formatINR(entry.emi)}</td>
                    <td className="px-4 py-2 text-right text-green-600">{formatINR(entry.principal)}</td>
                    <td className="px-4 py-2 text-right text-red-500">{formatINR(entry.interest)}</td>
                    <td className="px-4 py-2 text-right font-medium">{formatINR(entry.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
