"use client";

/**
 * components/search/FilterPanel.tsx
 *
 * Search filter sidebar.
 * All state lives in the URL — filter changes call router.push() so
 * the server component re-renders with fresh data. No local state needed
 * for filter values (only for UI toggle states like accordion open/close).
 *
 * Supports:
 *   - Remote-only toggle
 *   - Job type (full_time | contract | part_time | internship)
 *   - Experience level (entry | mid | senior | lead)
 *   - Min salary in INR (select)
 *   - Skills (multi-select chips)
 */

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ChevronDown, X } from "lucide-react";

// ------------------------------------------------------------------ //
// Types                                                                //
// ------------------------------------------------------------------ //

type JobType = "full_time" | "contract" | "part_time" | "internship";
type ExperienceLevel = "entry" | "mid" | "senior" | "lead";

const JOB_TYPE_LABELS: Record<JobType, string> = {
  full_time: "Full-time",
  contract: "Contract",
  part_time: "Part-time",
  internship: "Internship",
};

const EXPERIENCE_LABELS: Record<ExperienceLevel, string> = {
  entry: "Entry level",
  mid: "Mid level",
  senior: "Senior level",
  lead: "Lead / Principal",
};

const SALARY_OPTIONS = [
  { label: "Any", value: "" },
  { label: "₹3 LPA+",  value: "300000" },
  { label: "₹5 LPA+",  value: "500000" },
  { label: "₹8 LPA+",  value: "800000" },
  { label: "₹12 LPA+", value: "1200000" },
  { label: "₹20 LPA+", value: "2000000" },
  { label: "₹30 LPA+", value: "3000000" },
];

const POPULAR_SKILLS = [
  "python", "javascript", "typescript", "react", "node",
  "java", "go", "rust", "sql", "aws", "docker", "kubernetes",
];

// ------------------------------------------------------------------ //
// Component                                                            //
// ------------------------------------------------------------------ //

interface FilterPanelProps {
  /** Optionally hide on mobile — parent controls visibility. */
  className?: string;
}

export function FilterPanel({ className = "" }: FilterPanelProps) {
  const router = useRouter();
  const params = useSearchParams();
  const [skillsOpen, setSkillsOpen] = useState(true);

  // ── Helpers ─────────────────────────────────────────────────── //

  const get = (key: string) => params.get(key);
  const getAll = (key: string) => params.getAll(key);

  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params.toString());
    if (value === null || value === "") {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    next.delete("page"); // reset pagination whenever filter changes
    router.push(`/search?${next.toString()}`, { scroll: false });
  };

  const toggleArrayParam = (key: string, value: string) => {
    const next = new URLSearchParams(params.toString());
    const existing = next.getAll(key);
    if (existing.includes(value)) {
      // Remove — rebuild without this value
      next.delete(key);
      existing.filter((v) => v !== value).forEach((v) => next.append(key, v));
    } else {
      next.append(key, value);
    }
    next.delete("page");
    router.push(`/search?${next.toString()}`, { scroll: false });
  };

  const clearAll = () => {
    const next = new URLSearchParams();
    const q = params.get("q");
    if (q) next.set("q", q); // preserve search query
    router.push(`/search?${next.toString()}`, { scroll: false });
  };

  const activeFilterCount = [
    get("is_remote"),
    get("job_type"),
    get("experience_level"),
    get("salary_min"),
    ...getAll("skills"),
  ].filter(Boolean).length;

  // ── Render ──────────────────────────────────────────────────── //

  return (
    <aside
      className={[
        "w-64 shrink-0 space-y-5 rounded-xl border border-gray-200 bg-white p-5 self-start",
        className,
      ].join(" ")}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Filters</h2>
        {activeFilterCount > 0 && (
          <button
            onClick={clearAll}
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
          >
            <X size={12} />
            Clear all ({activeFilterCount})
          </button>
        )}
      </div>

      {/* ── Remote toggle ─────────────────────────────── */}
      <div>
        <label className="flex cursor-pointer items-center gap-3">
          <div className="relative">
            <input
              type="checkbox"
              className="peer sr-only"
              checked={get("is_remote") === "true"}
              onChange={(e) => setParam("is_remote", e.target.checked ? "true" : null)}
            />
            <div className="h-5 w-9 rounded-full bg-gray-200 peer-checked:bg-blue-600 transition-colors" />
            <div className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform peer-checked:translate-x-4" />
          </div>
          <span className="text-sm text-gray-700">Remote only</span>
        </label>
      </div>

      <Divider />

      {/* ── Job type ──────────────────────────────────── */}
      <FilterSection title="Job type">
        <div className="space-y-1.5">
          {(Object.entries(JOB_TYPE_LABELS) as [JobType, string][]).map(([val, label]) => (
            <RadioOption
              key={val}
              name="job_type"
              label={label}
              value={val}
              checked={get("job_type") === val}
              onChange={() =>
                setParam("job_type", get("job_type") === val ? null : val)
              }
            />
          ))}
        </div>
      </FilterSection>

      <Divider />

      {/* ── Experience ────────────────────────────────── */}
      <FilterSection title="Experience level">
        <div className="space-y-1.5">
          {(Object.entries(EXPERIENCE_LABELS) as [ExperienceLevel, string][]).map(([val, label]) => (
            <RadioOption
              key={val}
              name="experience"
              label={label}
              value={val}
              checked={get("experience_level") === val}
              onChange={() =>
                setParam("experience_level", get("experience_level") === val ? null : val)
              }
            />
          ))}
        </div>
      </FilterSection>

      <Divider />

      {/* ── Min salary ────────────────────────────────── */}
      <FilterSection title="Minimum salary">
        <select
          value={get("salary_min") || ""}
          onChange={(e) => setParam("salary_min", e.target.value || null)}
          className="w-full rounded-md border border-gray-200 px-2 py-1.5 text-sm text-gray-700 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
        >
          {SALARY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </FilterSection>

      <Divider />

      {/* ── Skills (multi-select chips) ────────────────── */}
      <FilterSection
        title="Skills"
        action={
          <button
            onClick={() => setSkillsOpen((o) => !o)}
            className="text-gray-400 hover:text-gray-600"
          >
            <ChevronDown
              size={14}
              className={`transition-transform ${skillsOpen ? "rotate-180" : ""}`}
            />
          </button>
        }
      >
        {skillsOpen && (
          <div className="flex flex-wrap gap-1.5">
            {POPULAR_SKILLS.map((skill) => {
              const active = getAll("skills").includes(skill);
              return (
                <button
                  key={skill}
                  onClick={() => toggleArrayParam("skills", skill)}
                  className={[
                    "rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
                    active
                      ? "border-blue-200 bg-blue-50 text-blue-700"
                      : "border-gray-200 bg-white text-gray-600 hover:border-gray-300",
                  ].join(" ")}
                >
                  {skill}
                </button>
              );
            })}
          </div>
        )}
      </FilterSection>
    </aside>
  );
}

// ------------------------------------------------------------------ //
// Sub-components                                                       //
// ------------------------------------------------------------------ //

function Divider() {
  return <hr className="border-gray-100" />;
}

function FilterSection({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

function RadioOption({
  name,
  label,
  value,
  checked,
  onChange,
}: {
  name: string;
  label: string;
  value: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5">
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={onChange}
        className="h-3.5 w-3.5 accent-blue-600"
      />
      <span className={`text-sm ${checked ? "font-medium text-gray-900" : "text-gray-600"}`}>
        {label}
      </span>
    </label>
  );
}
