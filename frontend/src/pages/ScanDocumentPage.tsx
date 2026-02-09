import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useDropzone } from "react-dropzone";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import api from "../lib/api";
import type { ScanJob } from "../types";

const STATUS_CONFIG = {
  uploaded: { icon: Upload, color: "text-blue-500", key: "scanner.statusUploaded" },
  processing: { icon: Loader2, color: "text-yellow-500", key: "scanner.statusProcessing" },
  completed: { icon: CheckCircle, color: "text-green-500", key: "scanner.statusCompleted" },
  review_needed: { icon: AlertCircle, color: "text-orange-500", key: "scanner.statusReviewNeeded" },
  failed: { icon: AlertCircle, color: "text-red-500", key: "scanner.statusFailed" },
};

export function ScanDocumentPage() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [jobId, setJobId] = useState<string | null>(null);
  const [editFields, setEditFields] = useState<Record<string, string>>({});

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/api/scanner/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: (data) => {
      setJobId(data.job_id);
    },
  });

  const { data: scanStatus } = useQuery<ScanJob>({
    queryKey: ["scan-status", jobId],
    queryFn: () => api.get(`/api/scanner/status/${jobId}`).then((r) => r.data),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "processing" || status === "uploaded" ? 2000 : false;
    },
  });

  const confirmMutation = useMutation({
    mutationFn: (data: Record<string, string>) =>
      api.post(`/api/scanner/${jobId}/confirm`, {
        bank_name: data.bank_name || "Unknown",
        loan_type: data.loan_type || "personal",
        principal_amount: Number(data.principal_amount) || 0,
        outstanding_principal: Number(data.outstanding_principal || data.principal_amount) || 0,
        interest_rate: Number(data.interest_rate) || 0,
        tenure_months: Number(data.tenure_months) || 0,
        remaining_tenure_months: Number(data.remaining_tenure_months || data.tenure_months) || 0,
        emi_amount: Number(data.emi_amount) || 0,
      }),
    onSuccess: (res) => {
      navigate(`/loans/${res.data.loan_id}`);
    },
  });

  const onDrop = useCallback((files: File[]) => {
    if (files[0]) uploadMutation.mutate(files[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
    },
    maxSize: 10 * 1024 * 1024,
    maxFiles: 1,
  });

  // Initialize edit fields from scan results
  useEffect(() => {
    if (scanStatus?.extracted_fields && Object.keys(editFields).length === 0) {
      const initial: Record<string, string> = {};
      scanStatus.extracted_fields.forEach((f) => { initial[f.field_name] = f.value; });
      setEditFields(initial);
    }
  }, [scanStatus]);

  const statusConfig = scanStatus ? STATUS_CONFIG[scanStatus.status] : null;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-gray-900">{t("scanner.title")}</h1>

      {/* Upload Zone */}
      {!jobId && (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
            isDragActive ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-blue-300 hover:bg-gray-50"
          }`}
        >
          <input {...getInputProps()} />
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="font-medium text-gray-700 mb-1">
            {isDragActive ? t("scanner.dropActive") : t("scanner.dropPrompt")}
          </p>
          <p className="text-sm text-gray-400">{t("scanner.formatHint")}</p>
          {uploadMutation.isPending && <p className="mt-3 text-blue-600">{t("scanner.uploading")}</p>}
          {uploadMutation.isError && <p className="mt-3 text-red-500">{t("scanner.uploadFailed")}</p>}
        </div>
      )}

      {/* Scan Progress */}
      {jobId && scanStatus && (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-4">
            {statusConfig && (
              <>
                <statusConfig.icon className={`w-6 h-6 ${statusConfig.color} ${scanStatus.status === "processing" ? "animate-spin" : ""}`} />
                <span className={`font-medium ${statusConfig.color}`}>{t(statusConfig.key)}</span>
              </>
            )}
          </div>

          {scanStatus.error_message && (
            <p className="text-sm text-red-500 mb-4">{scanStatus.error_message}</p>
          )}

          {/* Extracted Fields */}
          {scanStatus.extracted_fields && (
            <div className="space-y-3">
              <h3 className="font-medium text-gray-900">{t("scanner.extractedInfo")}</h3>
              {scanStatus.extracted_fields.map((field) => (
                <div key={field.field_name} className="flex items-center gap-3">
                  <label className="w-36 text-sm text-gray-500 capitalize">
                    {field.field_name.replace(/_/g, " ")}
                  </label>
                  <input
                    value={editFields[field.field_name] || ""}
                    onChange={(e) => setEditFields((prev) => ({ ...prev, [field.field_name]: e.target.value }))}
                    className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                  />
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    field.confidence > 0.8 ? "bg-green-100 text-green-700" :
                    field.confidence > 0.5 ? "bg-yellow-100 text-yellow-700" :
                    "bg-red-100 text-red-700"
                  }`}>
                    {Math.round(field.confidence * 100)}%
                  </span>
                </div>
              ))}

              <button
                onClick={() => confirmMutation.mutate(editFields)}
                disabled={confirmMutation.isPending}
                className="w-full mt-4 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {confirmMutation.isPending ? t("scanner.creatingLoan") : t("scanner.confirmCreate")}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
