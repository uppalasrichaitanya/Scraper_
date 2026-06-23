"use client";

/**
 * app/(app)/profile/page.tsx
 *
 * User profile page with resume upload and parsed profile display.
 * Client component — auth check happens via the API call (401 → redirect).
 */

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { User, FileText, Sparkles, ArrowLeft } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { ResumeUpload } from "@/components/profile/ResumeUpload";
import Link from "next/link";

export default function ProfilePage() {
  const router = useRouter();

  const { data: user, isLoading, error } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.auth.me(),
    retry: false,
  });

  // Redirect on 401
  useEffect(() => {
    if (error instanceof ApiError && error.status === 401) {
      router.push("/auth/login?redirect=/profile");
    }
  }, [error, router]);

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="h-32 bg-gray-100 rounded-xl" />
          <div className="h-48 bg-gray-100 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!user) return null; // Will redirect

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Back link */}
      <Link
        href="/search"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to jobs
      </Link>

      {/* Profile header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-100 border border-blue-200">
          <User className="h-7 w-7 text-blue-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {user.name || "Your Profile"}
          </h1>
          <p className="text-sm text-gray-500">{user.email}</p>
        </div>
      </div>

      {/* Resume section */}
      <section className="mb-8" aria-label="Resume upload">
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100">
            <FileText className="h-4 w-4 text-blue-600" />
          </div>
          <div>
            <h2 className="font-semibold text-base text-gray-900">Resume</h2>
            <p className="text-xs text-gray-500">
              Upload your resume to enable AI-powered job matching
            </p>
          </div>
        </div>
        <ResumeUpload />
      </section>

      {/* AI matching info */}
      <section
        className="rounded-xl border border-gray-200 bg-gradient-to-br from-blue-50/50 to-white p-5"
        aria-label="How matching works"
      >
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-5 w-5 text-blue-600" />
          <h2 className="font-semibold text-sm text-gray-900">
            How AI matching works
          </h2>
        </div>
        <ol className="space-y-2.5 text-sm text-gray-600">
          <li className="flex gap-3">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-[11px] font-bold text-blue-700 flex-shrink-0 mt-0.5">
              1
            </span>
            <span>Upload your resume — AI extracts your skills, experience, and education.</span>
          </li>
          <li className="flex gap-3">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-[11px] font-bold text-blue-700 flex-shrink-0 mt-0.5">
              2
            </span>
            <span>Your profile is converted into an AI embedding — a semantic fingerprint of your career.</span>
          </li>
          <li className="flex gap-3">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-[11px] font-bold text-blue-700 flex-shrink-0 mt-0.5">
              3
            </span>
            <span>Every job listing gets matched against your profile — you'll see match scores on every job card.</span>
          </li>
        </ol>
      </section>
    </div>
  );
}
