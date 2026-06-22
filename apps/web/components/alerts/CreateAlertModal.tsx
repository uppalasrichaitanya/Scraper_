"use client";

/**
 * components/alerts/CreateAlertModal.tsx
 *
 * Modal to create a job alert from the current search params.
 * Captures q, location, is_remote, job_type, salary_min, skills
 * from the URL and POSTs them to /api/v1/alerts.
 */

import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { Bell, X, Check, Loader2 } from "lucide-react";

type Frequency = "daily" | "weekly";
type ModalState = "idle" | "loading" | "success" | "error";

interface CreateAlertModalProps {
  onClose: () => void;
}

export function CreateAlertModal({ onClose }: CreateAlertModalProps) {
  const searchParams = useSearchParams();
  const firstInputRef = useRef<HTMLInputElement>(null);

  // Pre-fill alert name from current search query
  const q = searchParams.get("q");
  const location = searchParams.get("location");
  const defaultName = [q, location ? `in ${location}` : null]
    .filter(Boolean)
    .join(" ")
    .trim() || "All jobs";

  const [name, setName] = useState(defaultName + " alerts");
  const [frequency, setFrequency] = useState<Frequency>("daily");
  const [state, setState] = useState<ModalState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  // Trap focus and handle Escape key
  useEffect(() => {
    firstInputRef.current?.focus();

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  // Build query params from URL
  const buildQueryParams = () => {
    const params: Record<string, unknown> = {};
    if (q) params.q = q;
    if (searchParams.get("location")) params.location = searchParams.get("location");
    if (searchParams.get("is_remote")) params.is_remote = searchParams.get("is_remote") === "true";
    if (searchParams.get("job_type")) params.job_type = searchParams.get("job_type");
    if (searchParams.get("salary_min")) params.salary_min = parseInt(searchParams.get("salary_min")!, 10);
    const skills = searchParams.getAll("skills");
    if (skills.length) params.skills = skills;
    return params;
  };

  const handleCreate = async () => {
    if (!name.trim()) return;
    setState("loading");
    setErrorMsg("");

    try {
      const res = await fetch("/api/v1/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          name: name.trim(),
          frequency,
          query_params: buildQueryParams(),
        }),
      });

      if (res.status === 401) {
        setState("error");
        setErrorMsg("You need to be logged in to create alerts.");
        return;
      }
      if (res.status === 400) {
        const data = await res.json();
        setState("error");
        setErrorMsg(data.detail || "Something went wrong.");
        return;
      }
      if (!res.ok) {
        setState("error");
        setErrorMsg("Failed to create alert. Please try again.");
        return;
      }

      setState("success");
      // Auto-close after showing success state
      setTimeout(onClose, 1800);
    } catch {
      setState("error");
      setErrorMsg("Network error. Please check your connection.");
    }
  };

  // ── Render ─────────────────────────────────────────────────── //

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="alert-modal-title"
    >
      <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100">
              <Bell size={16} className="text-blue-600" />
            </div>
            <h2 id="alert-modal-title" className="text-base font-semibold text-gray-900">
              Create job alert
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">

          {/* Alert name */}
          <div>
            <label htmlFor="alert-name" className="block text-sm font-medium text-gray-700 mb-1.5">
              Alert name
            </label>
            <input
              ref={firstInputRef}
              id="alert-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              placeholder="e.g. Python remote jobs"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
          </div>

          {/* Active filters summary */}
          {Object.keys(buildQueryParams()).length > 0 && (
            <div className="rounded-lg bg-gray-50 px-3.5 py-3">
              <p className="mb-1.5 text-xs font-medium text-gray-500 uppercase tracking-wide">
                Alert criteria
              </p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(buildQueryParams()).map(([key, val]) => (
                  <span
                    key={key}
                    className="rounded-full bg-white border border-gray-200 px-2.5 py-0.5 text-xs text-gray-600"
                  >
                    {key}: {Array.isArray(val) ? val.join(", ") : String(val)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Frequency */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Email frequency</p>
            <div className="grid grid-cols-2 gap-2">
              {(["daily", "weekly"] as Frequency[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setFrequency(f)}
                  className={[
                    "rounded-lg border py-2.5 text-sm font-medium transition-all",
                    frequency === f
                      ? "border-blue-600 bg-blue-600 text-white shadow-sm"
                      : "border-gray-200 bg-white text-gray-600 hover:border-gray-300",
                  ].join(" ")}
                >
                  {f === "daily" ? "Daily digest" : "Weekly digest"}
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-gray-400">
              {frequency === "daily"
                ? "Sent every morning at 8 AM IST with new matching jobs."
                : "Sent every Monday morning with the week's best matches."}
            </p>
          </div>

          {/* Error */}
          {state === "error" && (
            <p className="rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-600">
              {errorMsg}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 border-t border-gray-100 px-6 py-4">
          <button
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-200 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!name.trim() || state === "loading" || state === "success"}
            className={[
              "flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-all",
              state === "success"
                ? "bg-green-600 text-white"
                : "bg-blue-600 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50",
            ].join(" ")}
          >
            {state === "loading" && <Loader2 size={15} className="animate-spin" />}
            {state === "success" && <Check size={15} />}
            {state === "loading"
              ? "Creating…"
              : state === "success"
              ? "Alert created!"
              : "Create alert"}
          </button>
        </div>

      </div>
    </div>
  );
}
