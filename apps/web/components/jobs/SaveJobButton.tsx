"use client";

/**
 * components/jobs/SaveJobButton.tsx
 *
 * Bookmark toggle for a single job.
 * - Optimistic UI: flips immediately, reverts on error.
 * - Redirects to /auth/login if the user is not authenticated.
 * - Accepts an optional onSaveChange callback for parent state sync.
 */

import { useState, useTransition } from "react";
import { Bookmark } from "lucide-react";

interface SaveJobButtonProps {
  jobId: string;
  /** True if the current user has already saved this job. */
  initialSaved?: boolean;
  /** Called after a successful save/unsave with the new state. */
  onSaveChange?: (saved: boolean) => void;
  /** Additional Tailwind classes for the button wrapper. */
  className?: string;
}

export function SaveJobButton({
  jobId,
  initialSaved = false,
  onSaveChange,
  className = "",
}: SaveJobButtonProps) {
  const [saved, setSaved] = useState(initialSaved);
  const [isPending, startTransition] = useTransition();

  const toggle = async () => {
    // The presence of the httpOnly cookie is invisible to JS.
    // We attempt the request and handle 401 as the "not logged in" signal.
    const optimisticState = !saved;
    setSaved(optimisticState); // optimistic flip

    startTransition(async () => {
      try {
        const res = await fetch(`/api/v1/saved-jobs/${jobId}`, {
          method: optimisticState ? "POST" : "DELETE",
          credentials: "include", // send the httpOnly cookie
        });

        if (res.status === 401) {
          // Not authenticated — undo optimistic update and redirect
          setSaved(!optimisticState);
          const returnTo = encodeURIComponent(window.location.pathname + window.location.search);
          window.location.href = `/auth/login?redirect=${returnTo}`;
          return;
        }

        if (res.status === 409) {
          // Already saved (race condition) — treat as success
          setSaved(true);
          onSaveChange?.(true);
          return;
        }

        if (!res.ok) {
          // Unknown error — revert
          setSaved(!optimisticState);
          console.error("[SaveJobButton] unexpected status:", res.status);
          return;
        }

        onSaveChange?.(optimisticState);
      } catch (err) {
        // Network error — revert
        setSaved(!optimisticState);
        console.error("[SaveJobButton] fetch failed:", err);
      }
    });
  };

  return (
    <button
      onClick={toggle}
      disabled={isPending}
      aria-label={saved ? "Remove from saved jobs" : "Save this job"}
      aria-pressed={saved}
      title={saved ? "Saved — click to remove" : "Save job"}
      className={[
        "group flex items-center justify-center rounded-lg border p-2 transition-all duration-150",
        saved
          ? "border-blue-200 bg-blue-50 text-blue-600 hover:bg-blue-100"
          : "border-gray-200 bg-white text-gray-400 hover:border-gray-300 hover:text-gray-600",
        isPending ? "cursor-not-allowed opacity-60" : "cursor-pointer",
        className,
      ].join(" ")}
    >
      <Bookmark
        size={18}
        fill={saved ? "currentColor" : "none"}
        strokeWidth={2}
        className="transition-transform duration-150 group-hover:scale-110"
      />
    </button>
  );
}
