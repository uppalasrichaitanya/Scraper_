"use client";

/**
 * app/(app)/tracker/page.tsx
 *
 * Application tracker Kanban board.
 * Requires authentication — redirects on 401.
 */

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, KanbanSquare } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import KanbanBoard from "@/components/tracker/KanbanBoard";

export default function TrackerPage() {
  const router = useRouter();

  const { data: user, error } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.auth.me(),
    retry: false,
  });

  useEffect(() => {
    if (error instanceof ApiError && error.status === 401) {
      router.push("/auth/login?redirect=/tracker");
    }
  }, [error, router]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Dashboard
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100">
            <KanbanSquare className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Application Tracker</h1>
            <p className="text-sm text-gray-500">
              Drag cards between columns to update their status
            </p>
          </div>
        </div>
      </div>

      <KanbanBoard />
    </div>
  );
}
