"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";

interface FilterPanelProps {
  className?: string;
}

const JOB_TYPES = [
  { value: "full_time", label: "Full-time" },
  { value: "contract", label: "Contract" },
  { value: "internship", label: "Internship" },
  { value: "part_time", label: "Part-time" },
];

export default function FilterPanel({ className }: FilterPanelProps) {
  const router = useRouter();
  const params = useSearchParams();

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("cursor");
    router.push(`/search?${next.toString()}`, { scroll: false });
  }

  const isRemote = params.get("remote") === "true";
  const jobType = params.get("job_type");

  return (
    <aside className={cn("space-y-6", className)}>
      <div>
        <h3 className="text-sm font-semibold mb-3 text-foreground">
          Work type
        </h3>
        <label className="flex items-center gap-2 cursor-pointer group">
          <input
            id="filter-remote"
            type="checkbox"
            checked={isRemote}
            onChange={(e) =>
              setParam("remote", e.target.checked ? "true" : null)
            }
            className="rounded border-input"
          />
          <span className="text-sm group-hover:text-foreground text-muted-foreground transition-colors">
            Remote only
          </span>
        </label>
      </div>

      <div>
        <h3 className="text-sm font-semibold mb-3 text-foreground">
          Job type
        </h3>
        <div className="space-y-2">
          {JOB_TYPES.map(({ value, label }) => (
            <label
              key={value}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <input
                id={`filter-type-${value}`}
                type="radio"
                name="job_type"
                checked={jobType === value}
                onChange={() => setParam("job_type", value)}
                className="border-input"
              />
              <span className="text-sm group-hover:text-foreground text-muted-foreground transition-colors">
                {label}
              </span>
            </label>
          ))}
          {jobType && (
            <button
              onClick={() => setParam("job_type", null)}
              className="text-xs text-muted-foreground hover:text-foreground underline mt-1"
            >
              Clear filter
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
