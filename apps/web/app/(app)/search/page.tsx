"use client";

import { Suspense, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import JobCard, { JobCardSkeleton } from "@/components/job/JobCard";
import { FilterPanel } from "@/components/search/FilterPanel";
import SearchBar from "@/components/search/SearchBar";
import type { JobListParams } from "@/lib/types";

function SearchContent() {
  const router = useRouter();
  const params = useSearchParams();

  const cursor = params.get("cursor") ?? undefined;
  const q = params.get("q") ?? undefined;
  const location = params.get("location") ?? undefined;
  const skill = params.get("skill") ?? undefined;
  const remote = params.get("remote") === "true" ? true : undefined;

  const queryParams: JobListParams = {
    ...(q && { q }),
    ...(location && { location }),
    ...(skill && { skill }),
    ...(remote && { is_remote: true }),
    ...(cursor && { cursor }),
  };

  const { data, isLoading } = useQuery({
    queryKey: ["jobs", queryParams],
    queryFn: () => api.jobs.list(queryParams),
    staleTime: 60_000,
  });

  // Infinite scroll sentinel via IntersectionObserver
  const observer = useRef<IntersectionObserver | null>(null);
  const sentinelRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (!node || !data?.next_cursor) return;
      observer.current?.disconnect();
      observer.current = new IntersectionObserver(([entry]) => {
        if (!entry || !entry.isIntersecting || !data.next_cursor) return;
        
        const next = new URLSearchParams(params.toString());
        next.set("cursor", data.next_cursor);
        router.push(`/search?${next.toString()}`, { scroll: false });
      });
      observer.current.observe(node);
    },
    [data?.next_cursor, params, router],
  );

  return (
    <div className="flex gap-6 max-w-7xl mx-auto px-4 py-6">
      {/* Sidebar filters — hidden on mobile */}
      <aside className="w-64 flex-shrink-0 hidden lg:block">
        <FilterPanel />
      </aside>

      <main className="flex-1 min-w-0">
        <SearchBar className="mb-6" />

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <JobCardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <>
            <p className="text-sm text-muted-foreground mb-4">
              {data?.total != null
                ? `${data.total.toLocaleString("en-IN")} jobs found`
                : "Searching…"}
            </p>
            <div className="space-y-3">
              {data?.items.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
            {/* Infinite scroll sentinel */}
            <div ref={sentinelRef} className="h-8" />
          </>
        )}
      </main>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-12 text-sm text-gray-500">
          Loading search…
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
