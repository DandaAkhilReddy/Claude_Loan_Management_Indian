import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { formatINR } from "../lib/format";
import { calculateEMI, calculateTotalInterest } from "../lib/emi-math";

export function EMICalculatorPage() {
  const { t } = useTranslation();
  const [principal, setPrincipal] = useState(2000000);
  const [rate, setRate] = useState(8.5);
  const [tenureYears, setTenureYears] = useState(20);

  const result = useMemo(() => {
    const tenureMonths = tenureYears * 12;
    const emi = calculateEMI(principal, rate, tenureMonths);
    const totalInterest = calculateTotalInterest(principal, rate, tenureMonths);
    const totalPayment = principal + totalInterest;
    return { emi, totalInterest, totalPayment, tenureMonths };
  }, [principal, rate, tenureYears]);

  const interestPercent = result.totalPayment > 0 ? (result.totalInterest / result.totalPayment) * 100 : 0;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-gray-900">{t("emi.title")}</h1>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 space-y-6">
        {/* Principal Slider */}
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">{t("emi.principal")}</label>
            <span className="text-sm font-semibold text-blue-600">{formatINR(principal)}</span>
          </div>
          <input
            type="range"
            min={100000} max={50000000} step={100000}
            value={principal}
            onChange={(e) => setPrincipal(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>₹1L</span><span>₹5Cr</span>
          </div>
        </div>

        {/* Rate Slider */}
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">{t("emi.rate")}</label>
            <span className="text-sm font-semibold text-blue-600">{rate}%</span>
          </div>
          <input
            type="range"
            min={1} max={25} step={0.1}
            value={rate}
            onChange={(e) => setRate(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>1%</span><span>25%</span>
          </div>
        </div>

        {/* Tenure Slider */}
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">{t("emi.tenure")}</label>
            <span className="text-sm font-semibold text-blue-600">{tenureYears} years</span>
          </div>
          <input
            type="range"
            min={1} max={30} step={1}
            value={tenureYears}
            onChange={(e) => setTenureYears(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>1yr</span><span>30yr</span>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-blue-50 rounded-xl p-5 text-center">
          <p className="text-sm text-blue-600 mb-1">{t("emi.monthlyEmi")}</p>
          <p className="text-2xl font-bold text-blue-700">{formatINR(result.emi)}</p>
        </div>
        <div className="bg-red-50 rounded-xl p-5 text-center">
          <p className="text-sm text-red-600 mb-1">{t("emi.totalInterest")}</p>
          <p className="text-2xl font-bold text-red-700">{formatINR(result.totalInterest)}</p>
        </div>
        <div className="bg-green-50 rounded-xl p-5 text-center">
          <p className="text-sm text-green-600 mb-1">{t("emi.totalPayment")}</p>
          <p className="text-2xl font-bold text-green-700">{formatINR(result.totalPayment)}</p>
        </div>
      </div>

      {/* Visual Breakdown */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Payment Breakdown</h3>
        <div className="h-6 bg-gray-100 rounded-full overflow-hidden flex">
          <div className="bg-blue-500 h-full" style={{ width: `${100 - interestPercent}%` }} />
          <div className="bg-red-400 h-full" style={{ width: `${interestPercent}%` }} />
        </div>
        <div className="flex justify-between mt-2 text-xs">
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-500 rounded-full" /> Principal ({Math.round(100 - interestPercent)}%)</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-400 rounded-full" /> Interest ({Math.round(interestPercent)}%)</span>
        </div>
      </div>
    </div>
  );
}
