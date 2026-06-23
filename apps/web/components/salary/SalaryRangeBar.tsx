// components/salary/SalaryRangeBar.tsx
import React from "react";

interface Props {
  p25: number
  median: number
  p75: number
}

export function SalaryRangeBar({ p25, median, p75 }: Props) {
  // Normalize positions relative to p75 as the right edge
  const pctOf = (v: number) => Math.min(100, Math.max(0, Math.round((v / p75) * 100)))

  return (
    <div>
      <div className="relative h-3 w-full rounded-full bg-gray-100">
        {/* Filled range: p25 → p75 */}
        <div
          className="absolute h-3 rounded-full bg-blue-200"
          style={{ left: `${pctOf(p25)}%`, right: "0%" }}
        />
        {/* Median marker */}
        <div
          className="absolute top-1/2 h-5 w-1 -translate-y-1/2 rounded-full bg-blue-600"
          style={{ left: `${pctOf(median)}%` }}
        />
      </div>
      <div className="mt-2 flex justify-between text-xs text-gray-400">
        <span>₹{(p25 / 100000).toFixed(1)}L</span>
        <span className="font-medium text-blue-600">
          ₹{(median / 100000).toFixed(1)}L median
        </span>
        <span>₹{(p75 / 100000).toFixed(1)}L</span>
      </div>
    </div>
  )
}
