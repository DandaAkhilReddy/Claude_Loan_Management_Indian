import { formatINR } from "../../lib/format";
import type { Loan } from "../../types";

interface Props {
  loans: Loan[];
  selected: string[];
  onChange: (ids: string[]) => void;
}

export function StepSelectLoans({ loans, selected, onChange }: Props) {
  const toggleLoan = (id: string) => {
    onChange(
      selected.includes(id)
        ? selected.filter((s) => s !== id)
        : [...selected, id]
    );
  };

  const toggleAll = () => {
    onChange(selected.length === loans.length ? [] : loans.map((l) => l.id));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-gray-900">Select Loans to Optimize</h2>
        <button onClick={toggleAll} className="text-sm text-blue-600 hover:text-blue-700">
          {selected.length === loans.length ? "Deselect All" : "Select All"}
        </button>
      </div>

      <div className="space-y-2">
        {loans.map((loan) => (
          <label
            key={loan.id}
            className={`flex items-center gap-4 p-4 rounded-xl border cursor-pointer transition-colors ${
              selected.includes(loan.id) ? "border-blue-300 bg-blue-50" : "border-gray-200 hover:bg-gray-50"
            }`}
          >
            <input
              type="checkbox"
              checked={selected.includes(loan.id)}
              onChange={() => toggleLoan(loan.id)}
              className="rounded border-gray-300 text-blue-600 w-5 h-5"
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900">{loan.bank_name}</span>
                <span className="text-xs bg-gray-100 px-2 py-0.5 rounded capitalize">{loan.loan_type}</span>
              </div>
              <div className="text-sm text-gray-500 mt-0.5">
                {formatINR(loan.outstanding_principal)} at {loan.interest_rate}% — EMI {formatINR(loan.emi_amount)}
              </div>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}
