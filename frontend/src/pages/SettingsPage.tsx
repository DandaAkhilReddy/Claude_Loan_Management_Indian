import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";
import { useLanguageStore } from "../store/languageStore";

export function SettingsPage() {
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguageStore();
  const queryClient = useQueryClient();

  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: () => api.get("/api/auth/me").then((r) => r.data),
  });

  const [form, setForm] = useState({
    display_name: profile?.display_name || "",
    tax_regime: profile?.tax_regime || "old",
    annual_income: profile?.annual_income || "",
  });

  const updateProfile = useMutation({
    mutationFn: (data: any) => api.put("/api/auth/me", data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile"] }),
  });

  const exportData = useMutation({
    mutationFn: () => api.post("/api/user/export-data"),
  });

  const handleSave = () => {
    updateProfile.mutate({
      display_name: form.display_name || undefined,
      preferred_language: language,
      tax_regime: form.tax_regime,
      annual_income: form.annual_income ? Number(form.annual_income) : undefined,
    });
  };

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <h1 className="text-xl font-bold text-gray-900">{t("nav.settings")}</h1>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
          <input
            value={form.display_name}
            onChange={(e) => setForm((p) => ({ ...p, display_name: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="en">English</option>
            <option value="hi">हिन्दी (Hindi)</option>
            <option value="te">తెలుగు (Telugu)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tax Regime</label>
          <select value={form.tax_regime} onChange={(e) => setForm((p) => ({ ...p, tax_regime: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="old">Old Regime</option>
            <option value="new">New Regime</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Annual Income (₹)</label>
          <input
            type="number"
            value={form.annual_income}
            onChange={(e) => setForm((p) => ({ ...p, annual_income: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            placeholder="For tax optimization"
          />
        </div>

        <button
          onClick={handleSave}
          disabled={updateProfile.isPending}
          className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {updateProfile.isPending ? "Saving..." : t("common.save")}
        </button>
      </div>

      {/* Data Management */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 space-y-4">
        <h2 className="font-semibold text-gray-900">Data Management</h2>
        <button
          onClick={() => exportData.mutate()}
          className="w-full py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
        >
          Export My Data (DPDP Act)
        </button>
        <button
          onClick={() => {
            if (confirm("This will permanently delete all your data. Are you sure?")) {
              api.delete("/api/user/delete-account");
            }
          }}
          className="w-full py-2 border border-red-300 rounded-lg text-sm text-red-600 hover:bg-red-50"
        >
          Delete Account
        </button>
        <p className="text-xs text-gray-400">App version: 0.1.0</p>
      </div>
    </div>
  );
}
