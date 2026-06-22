"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useRef, type ChangeEvent } from "react";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  className?: string;
}

export default function SearchBar({ className }: SearchBarProps) {
  const router = useRouter();
  const params = useSearchParams();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      const next = new URLSearchParams(params.toString());
      const val = e.target.value.trim();
      if (val) next.set("q", val);
      else next.delete("q");
      next.delete("cursor"); // reset pagination on new search
      router.push(`/search?${next.toString()}`, { scroll: false });
    }, 350);
  }

  return (
    <div className={cn("relative", className)}>
      <svg
        className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M21 21l-4.35-4.35M17 11A6 6 0 111 11a6 6 0 0116 0z"
        />
      </svg>
      <input
        id="job-search-input"
        type="search"
        defaultValue={params.get("q") ?? ""}
        onChange={handleChange}
        placeholder="Search jobs, skills, companies…"
        className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-input bg-background text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
      />
    </div>
  );
}
