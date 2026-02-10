import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus, ScanLine, Zap, TrendingDown, Brain, ChevronDown, ChevronUp, AlertTriangle, Shield, Sparkles } from "lucide-react";
import api from "../lib/api";
import { formatMonths } from "../lib/format";
import { CurrencyDisplay } from "../components/shared/CurrencyDisplay";
import { LoadingSpinner } from "../components/shared/LoadingSpinner";
import { EmptyState } from "../components/shared/EmptyState";
import type { Loan, DashboardSummary, LoanInsight } from "../types";

const LOAN_TYPE_COLORS: Record<string, string> = {
  home: "bg-blue-100 text-blue-700",
  personal: "bg-purple-100 text-purple-700",
  car: "bg-green-100 text-green-700",
  education: "bg-yellow-100 text-yellow-700",
  gold: "bg-amber-100 text-amber-700",
  credit_card: "bg-red-100 text-red-700",
  business: "bg-teal-100 text-teal-700",
};

export function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [expandedInsight, setExpandedInsight] = useState<string | null>(null);

  const { data: loans, isLoading } = useQuery<Loan[]>({
    queryKey: ["loans"],
    queryFn: () => api.get("/api/loans").then((r) => r.data),
  });

  const activeLoans = loans?.filter((l) => l.status === "active") || [];

  const { data: summary } = useQuery<DashboardSummary>({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.get("/api/optimizer/dashboard-summary").then((r) => r.data),
    enabled: activeLoans.length > 0,
  });

  const { data: insights } = useQuery<LoanInsight[]>({
    queryKey: ["loan-insights", activeLoans.map((l) => l.id).join(",")],
    queryFn: () =>
      api
        .post("/api/ai/explain-loans-batch", { loan_ids: activeLoans.map((l) => l.id) })
        .then((r) => r.data.insights),
    enabled: activeLoans.length > 0,
  });

  if (isLoading) return <LoadingSpinner size="lg" />;

  if (activeLoans.length === 0) {
    return (
      <EmptyState
        title={t("dashboard.noLoansYet")}
        description={t("dashboard.noLoansDesc")}
        action={{ label: t("dashboard.addLoan"), onClick: () => navigate("/loans?add=true") }}
      />
    );
  }

  const totalDebt = activeLoans.reduce((sum, l) => sum + l.outstanding_principal, 0);
  const totalEMI = activeLoans.reduce((sum, l) => sum + l.emi_amount, 0);
  const maxTenure = Math.max(...activeLoans.map((l) => l.remaining_tenure_months));
  const avgRate = activeLoans.reduce((sum, l) => sum + l.interest_rate, 0) / activeLoans.length;
  const highestRateLoan = activeLoans.reduce((max, l) => (l.interest_rate > max.interest_rate ? l : max), activeLoans[0]);

  const insightMap = new Map(insights?.map((i) => [i.loan_id, i.text]) || []);

  return (
    <div className="space-y-6">
      {/* AI Optimizer Summary Card */}
      {summary?.has_loans && summary.interest_saved > 0 && (
        <div className="bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl p-5 text-white shadow-lg">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-emerald-100">{t("dashboard.aiRecommendation")}</p>
              <p className="text-lg font-bold mt-1">
                {t("dashboard.youCouldSave")}{" "}
                <CurrencyDisplay amount={summary.interest_saved} className="text-white" />{" "}
                {t("dashboard.inInterest")}
              </p>
              <p className="text-sm text-emerald-100 mt-1">
                {t("dashboard.byPaying")}{" "}
                <CurrencyDisplay amount={summary.suggested_extra} className="text-white" />{" "}
                {t("dashboard.extraPerMonth")} · {summary.months_saved} {t("dashboard.monthsFaster")}
              </p>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={() => navigate("/optimizer")}
                  className="px-3 py-1.5 bg-white text-emerald-700 rounded-lg text-sm font-medium hover:bg-emerald-50"
                >
                  {t("dashboard.viewStrategies")}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500 mb-1">{t("dashboard.totalDebt")}</p>
          <CurrencyDisplay amount={totalDebt} className="text-2xl font-bold text-gray-900" />
          <p className="text-xs text-gray-400 mt-1">{t("dashboard.activeLoans", { count: activeLoans.length })}</p>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500 mb-1">{t("dashboard.monthlyEmi")}</p>
          <CurrencyDisplay amount={totalEMI} className="text-2xl font-bold text-gray-900" />
          <p className="text-xs text-gray-400 mt-1">{t("dashboard.perMonth")}</p>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500 mb-1">{t("dashboard.debtFreeBy")}</p>
          <p className="text-2xl font-bold text-gray-900">
            {summary?.debt_free_months ? formatMonths(summary.debt_free_months) : formatMonths(maxTenure)}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {summary?.debt_free_months
              ? t("dashboard.withOptimization")
              : t("dashboard.longestRemaining")}
          </p>
        </div>
      </div>

      {/* Portfolio Health */}
      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="w-5 h-5 text-blue-500" />
          <h2 className="font-semibold text-gray-900">{t("dashboard.portfolioHealth")}</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-gray-500">{t("dashboard.avgRate")}</p>
            <p className={`text-lg font-bold ${avgRate > 15 ? "text-red-600" : avgRate > 10 ? "text-yellow-600" : "text-green-600"}`}>
              {avgRate.toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">{t("dashboard.highestRisk")}</p>
            <div className="flex items-center gap-1">
              <AlertTriangle className={`w-4 h-4 ${highestRateLoan.interest_rate > 15 ? "text-red-500" : "text-yellow-500"}`} />
              <span className="text-sm font-medium text-gray-900">
                {highestRateLoan.bank_name} ({highestRateLoan.interest_rate}%)
              </span>
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500">{t("dashboard.debtToEmi")}</p>
            <p className="text-lg font-bold text-gray-900">
              {totalEMI > 0 ? Math.round(totalDebt / totalEMI) : 0} {t("common.months")}
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => navigate("/loans?add=true")}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          {t("dashboard.addLoan")}
        </button>
        <button
          onClick={() => navigate("/scanner")}
          className="flex items-center gap-2 px-4 py-2 bg-white text-gray-700 rounded-lg text-sm font-medium border border-gray-300 hover:bg-gray-50"
        >
          <ScanLine className="w-4 h-4" />
          {t("dashboard.scanDoc")}
        </button>
        <button
          onClick={() => navigate("/optimizer")}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg text-sm font-medium hover:from-indigo-600 hover:to-purple-700"
        >
          <Zap className="w-4 h-4" />
          {t("dashboard.runOptimizer")}
        </button>
      </div>

      {/* Strategy Preview */}
      {summary?.strategies_preview && summary.strategies_preview.length > 0 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-3">
            <TrendingDown className="w-5 h-5 text-indigo-500" />
            <h2 className="font-semibold text-gray-900">{t("dashboard.strategyPreview")}</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {summary.strategies_preview.map((s) => (
              <div
                key={s.name}
                className={`p-3 rounded-lg border ${
                  s.name === summary.recommended_strategy
                    ? "border-emerald-300 bg-emerald-50"
                    : "border-gray-200"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700 capitalize">{s.name.replace(/_/g, " ")}</span>
                  {s.name === summary.recommended_strategy && (
                    <span className="text-xs bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">
                      {t("optimizer.strategy.recommended")}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500">
                  {t("optimizer.interestSaved")}:{" "}
                  <CurrencyDisplay amount={s.interest_saved} compact className="font-medium text-gray-900" />
                </p>
                <p className="text-xs text-gray-500">
                  {t("optimizer.monthsSaved")}: <span className="font-medium text-gray-900">{s.months_saved}</span>
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Loan Cards with AI Insights */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">{t("dashboard.yourLoans")}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {activeLoans.map((loan) => {
            const insight = insightMap.get(loan.id);
            const isExpanded = expandedInsight === loan.id;
            return (
              <div
                key={loan.id}
                className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden"
              >
                <div
                  onClick={() => navigate(`/loans/${loan.id}`)}
                  className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium text-gray-900">{loan.bank_name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${LOAN_TYPE_COLORS[loan.loan_type] || "bg-gray-100 text-gray-600"}`}>
                      {loan.loan_type}
                    </span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">{t("loans.outstanding")}</span>
                      <CurrencyDisplay amount={loan.outstanding_principal} className="font-medium text-gray-900" />
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">{t("loans.rate")}</span>
                      <span className="font-medium text-gray-900">{loan.interest_rate}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">{t("loans.emi")}</span>
                      <CurrencyDisplay amount={loan.emi_amount} className="font-medium text-gray-900" />
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">{t("loans.remaining")}</span>
                      <span className="font-medium text-gray-900">{formatMonths(loan.remaining_tenure_months)}</span>
                    </div>
                  </div>
                  {/* Progress bar */}
                  <div className="mt-3">
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${Math.max(5, (1 - loan.outstanding_principal / loan.principal_amount) * 100)}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {Math.round((1 - loan.outstanding_principal / loan.principal_amount) * 100)}% {t("dashboard.paid")}
                    </p>
                  </div>
                </div>

                {/* AI Insight Toggle */}
                {insight && (
                  <div className="border-t border-gray-100">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setExpandedInsight(isExpanded ? null : loan.id);
                      }}
                      className="w-full px-4 py-2 flex items-center gap-2 text-xs text-indigo-600 hover:bg-indigo-50 transition-colors"
                    >
                      <Brain className="w-3.5 h-3.5" />
                      <span className="font-medium">{t("dashboard.aiInsight")}</span>
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5 ml-auto" /> : <ChevronDown className="w-3.5 h-3.5 ml-auto" />}
                    </button>
                    {isExpanded && (
                      <div className="px-4 pb-3 text-xs text-gray-600 leading-relaxed">
                        {insight}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
