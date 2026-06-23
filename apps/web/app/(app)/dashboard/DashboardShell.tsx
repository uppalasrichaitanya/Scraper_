"use client";

/**
 * app/(app)/dashboard/DashboardShell.tsx
 *
 * Client-side dashboard with:
 *  - Saved job stats (count by status)
 *  - Resume parse status + CTA
 *  - Recent saved jobs
 *  - Quick actions
 */

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";
import {
  Bookmark,
  FileText,
  Search,
  Sparkles,
  BriefcaseBusiness,
  ArrowRight,
  Loader2,
  Bell,
  KanbanSquare,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { SavedJobStatus } from "@/lib/types";
import { timeAgo } from "@/lib/utils";

const STATUS_COLOURS: Record<SavedJobStatus, { bg: string; text: string; dot: string }> = {
  saved:        { bg: "bg-gray-50",   text: "text-gray-700",   dot: "bg-gray-400"   },
  applied:      { bg: "bg-blue-50",   text: "text-blue-700",   dot: "bg-blue-500"   },
  interviewing: { bg: "bg-yellow-50", text: "text-yellow-700", dot: "bg-yellow-500" },
  offered:      { bg: "bg-green-50",  text: "text-green-700",  dot: "bg-green-500"  },
  rejected:     { bg: "bg-red-50",    text: "text-red-700",    dot: "bg-red-400"    },
};

export default function DashboardShell() {
  const router = useRouter();

  // ── Auth check ────────────────────────────────────────────────
  const { data: user, error: userError, isLoading: userLoading } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.auth.me(),
    retry: false,
  });

  useEffect(() => {
    if (userError instanceof ApiError && userError.status === 401) {
      router.push("/auth/login?redirect=/dashboard");
    }
  }, [userError, router]);

  // ── Saved jobs ────────────────────────────────────────────────
  const { data: savedJobsData, isLoading: savedLoading } = useQuery({
    queryKey: ["saved-jobs"],
    queryFn: () => api.savedJobs.list(),
    enabled: !!user,
  });

  // ── Resume status ─────────────────────────────────────────────
  const { data: parseStatus } = useQuery({
    queryKey: ["resume-status"],
    queryFn: () => api.resume.status(),
    enabled: !!user,
  });

  // ── Loading state ─────────────────────────────────────────────
  if (userLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="flex items-center justify-center gap-3 py-24">
          <Loader2 className="h-6 w-6 text-blue-500 animate-spin" />
          <p className="text-sm text-gray-500">Loading dashboard…</p>
        </div>
      </div>
    );
  }

  if (!user) return null;

  const savedJobs = savedJobsData?.items ?? [];
  const recentJobs = savedJobs.slice(0, 5);

  // Status counts
  const statusCounts: Record<SavedJobStatus, number> = {
    saved: 0,
    applied: 0,
    interviewing: 0,
    offered: 0,
    rejected: 0,
  };
  for (const sj of savedJobs) {
    if (sj.status in statusCounts) {
      statusCounts[sj.status]++;
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back{user.name ? `, ${user.name}` : ""}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Here's an overview of your job search.
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
        {(Object.entries(statusCounts) as [SavedJobStatus, number][]).map(
          ([status, count]) => {
            const colours = STATUS_COLOURS[status];
            return (
              <div
                key={status}
                className={`rounded-xl border p-4 ${colours.bg} border-transparent`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className={`h-2 w-2 rounded-full ${colours.dot}`} />
                  <span className={`text-xs font-medium capitalize ${colours.text}`}>
                    {status}
                  </span>
                </div>
                <p className={`text-2xl font-bold ${colours.text}`}>{count}</p>
              </div>
            );
          },
        )}
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Left column — Recent saved jobs */}
        <div className="md:col-span-2 space-y-6">
          <div className="rounded-xl border border-gray-200 bg-white">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Bookmark className="h-4 w-4 text-blue-600" />
                <h2 className="font-semibold text-sm text-gray-900">
                  Recent saved jobs
                </h2>
              </div>
              <Link
                href="/tracker"
                className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
              >
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {savedLoading ? (
              <div className="p-5">
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-14 bg-gray-50 rounded-lg animate-pulse" />
                  ))}
                </div>
              </div>
            ) : recentJobs.length === 0 ? (
              <div className="p-8 text-center">
                <BriefcaseBusiness className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500 mb-3">No saved jobs yet</p>
                <Link
                  href="/search"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                >
                  <Search className="h-4 w-4" />
                  Find jobs
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-gray-50">
                {recentJobs.map((sj) => {
                  const colours = STATUS_COLOURS[sj.status];
                  return (
                    <Link
                      key={sj.id}
                      href={`/jobs/${sj.job_id}`}
                      className="flex items-center gap-3 px-5 py-3.5 hover:bg-gray-50/50 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {sj.job?.title ?? "Job"}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {sj.job?.company_name ?? "Unknown"}{" "}
                          {sj.job?.location_city ? `· ${sj.job.location_city}` : ""}
                        </p>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${colours.bg} ${colours.text}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${colours.dot}`} />
                        {sj.status}
                      </span>
                      <span className="text-[11px] text-gray-400 flex-shrink-0">
                        {timeAgo(sj.saved_at)}
                      </span>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right column — Quick actions + resume status */}
        <div className="space-y-4">
          {/* Resume status */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <div className="flex items-center gap-2 mb-3">
              <FileText className="h-4 w-4 text-blue-600" />
              <h2 className="font-semibold text-sm text-gray-900">Resume</h2>
            </div>
            {parseStatus?.is_parsed ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-green-600">
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-xs font-medium">Parsed</span>
                </div>
                {parseStatus.current_title && (
                  <p className="text-sm text-gray-700">{parseStatus.current_title}</p>
                )}
                <p className="text-xs text-gray-400">
                  {parseStatus.skills_count} skills extracted
                </p>
                <Link
                  href="/profile"
                  className="text-xs text-blue-600 hover:underline font-medium"
                >
                  Update resume →
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-gray-500">
                  Upload your resume to unlock AI match scores.
                </p>
                <Link
                  href="/profile"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                >
                  <Sparkles className="h-4 w-4" />
                  Upload resume
                </Link>
              </div>
            )}
          </div>

          {/* Quick actions */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="font-semibold text-sm text-gray-900 mb-3">Quick actions</h2>
            <nav className="space-y-1.5">
              {[
                { href: "/search", icon: Search, label: "Search jobs" },
                { href: "/tracker", icon: KanbanSquare, label: "Application tracker" },
                { href: "/profile", icon: FileText, label: "My profile" },
                { href: "/alerts", icon: Bell, label: "Job alerts" },
              ].map(({ href, icon: Icon, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
                >
                  <Icon className="h-4 w-4 text-gray-400" />
                  {label}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      </div>
    </div>
  );
}
