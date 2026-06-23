"use client";

/**
 * components/job/MatchScoreBadge.tsx
 *
 * Displays an AI match percentage badge when the backend returns a
 * match_score for the authenticated user.  Score tiers:
 *   ≥ 80%  → green (strong match)
 *   ≥ 60%  → blue  (good match)
 *   ≥ 40%  → amber (partial match)
 *    < 40% → gray  (low match)
 */

import { Sparkles } from "lucide-react";

interface MatchScoreBadgeProps {
  /** 0–1 float from the API's cosine-similarity score */
  score: number;
  /** Compact mode for kanban cards — smaller text, no icon */
  compact?: boolean;
}

const tiers = [
  { min: 0.8, label: "Strong match", bg: "bg-green-50",  text: "text-green-700", border: "border-green-200", dot: "bg-green-500" },
  { min: 0.6, label: "Good match",   bg: "bg-blue-50",   text: "text-blue-700",  border: "border-blue-200",  dot: "bg-blue-500"  },
  { min: 0.4, label: "Partial match", bg: "bg-amber-50",  text: "text-amber-700", border: "border-amber-200", dot: "bg-amber-500" },
  { min: 0,   label: "Low match",     bg: "bg-gray-50",   text: "text-gray-600",  border: "border-gray-200",  dot: "bg-gray-400"  },
] as const;

function getTier(score: number) {
  for (const t of tiers) {
    if (score >= t.min) return t;
  }
  return tiers[tiers.length - 1]!;
}

export function MatchScoreBadge({ score, compact = false }: MatchScoreBadgeProps) {
  const pct = Math.round(score * 100);
  const tier = getTier(score);

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-semibold ${tier.bg} ${tier.text} ${tier.border}`}
        title={`${tier.label} — ${pct}%`}
      >
        <span className={`inline-block h-1.5 w-1.5 rounded-full ${tier.dot}`} />
        {pct}%
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold transition-colors ${tier.bg} ${tier.text} ${tier.border}`}
      title={`${tier.label} — ${pct}% match based on your resume`}
    >
      <Sparkles className="h-3.5 w-3.5" />
      {pct}% match
    </span>
  );
}
