import { useState } from "react";
import { formatINR } from "../../lib/format";

interface Props {
  monthlyExtra: number;
  onMonthlyExtraChange: (value: number) => void;
  lumpSums: { month: number; amount: number }[];
  onLumpSumsChange: (sums: { month: number; amount: number }[]) => void;
}

export function StepSetBudget({ monthlyExtra, onMonthlyExtraChange, lumpSums, onLumpSumsChange }: Props) {
  const [gullakMode, setGullakMode] = useState(false);
  const [dailySaving, setDailySaving] = useState(100);

  const handleGullakToggle = () => {
    if (!gullakMode) {
      onMonthlyExtraChange(dailySaving * 30);
    }
    setGullakMode(!gullakMode);
  };

  const handleDailyChange = (value: number) => {
    setDailySaving(value);
    if (gullakMode) onMonthlyExtraChange(value * 30);
  };

  const addLumpSum = () => {
    onLumpSumsChange([...lumpSums, { month: 6, amount: 50000 }]);
  };

  return (
    <div className="space-y-6">
      <h2 className="font-semibold text-gray-900">How much extra can you pay?</h2>

      {/* Gullak Mode Toggle */}
      <div className="flex items-center justify-between p-4 bg-amber-50 rounded-xl border border-amber-200">
        <div>
          <p className="font-medium text-amber-800">Gullak Mode</p>
          <p className="text-sm text-amber-600">Think in daily savings — easier to commit!</p>
        </div>
        <button
          onClick={handleGullakToggle}
          className={`relative w-12 h-6 rounded-full transition-colors ${gullakMode ? "bg-amber-500" : "bg-gray-300"}`}
        >
          <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${gullakMode ? "translate-x-6" : "translate-x-0.5"}`} />
        </button>
      </div>

      {gullakMode ? (
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">Daily Saving</label>
            <span className="text-sm font-semibold text-amber-600">{formatINR(dailySaving)}/day = {formatINR(dailySaving * 30)}/month</span>
          </div>
          <input
            type="range" min={10} max={1000} step={10}
            value={dailySaving}
            onChange={(e) => handleDailyChange(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-amber-500"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>₹10/day</span><span>₹1,000/day</span>
          </div>
        </div>
      ) : (
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">Monthly Extra Payment</label>
            <span className="text-sm font-semibold text-blue-600">{formatINR(monthlyExtra)}</span>
          </div>
          <input
            type="range" min={0} max={50000} step={500}
            value={monthlyExtra}
            onChange={(e) => onMonthlyExtraChange(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>₹0</span><span>₹50,000</span>
          </div>
        </div>
      )}

      {/* Lump Sums */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">Lump Sum Payments (bonuses, windfalls)</label>
          <button onClick={addLumpSum} className="text-sm text-blue-600 hover:text-blue-700">+ Add</button>
        </div>
        {lumpSums.map((ls, i) => (
          <div key={i} className="flex gap-3 mb-2">
            <div className="flex-1">
              <input
                type="number" placeholder="Amount (₹)"
                value={ls.amount}
                onChange={(e) => {
                  const updated = [...lumpSums];
                  updated[i].amount = Number(e.target.value);
                  onLumpSumsChange(updated);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
            <div className="w-24">
              <input
                type="number" placeholder="Month"
                value={ls.month}
                onChange={(e) => {
                  const updated = [...lumpSums];
                  updated[i].month = Number(e.target.value);
                  onLumpSumsChange(updated);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
            <button
              onClick={() => onLumpSumsChange(lumpSums.filter((_, j) => j !== i))}
              className="text-red-500 hover:text-red-600 text-sm"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
