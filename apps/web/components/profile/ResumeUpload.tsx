"use client";

/**
 * components/profile/ResumeUpload.tsx
 *
 * Resume upload widget — drag-and-drop or click-to-browse.
 * Accepts PDF and DOCX, max 5 MB.
 * Shows upload progress, parse status, and parsed profile summary.
 */

import { useState, useRef, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  X,
} from "lucide-react";
import { api } from "@/lib/api";

type UploadState = "idle" | "uploading" | "success" | "error";

const ACCEPTED = ".pdf,.docx";
const MAX_SIZE = 5 * 1024 * 1024; // 5 MB

export function ResumeUpload() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [dragOver, setDragOver] = useState(false);

  // ── Parse status polling ──────────────────────────────────────
  const { data: parseStatus } = useQuery({
    queryKey: ["resume-status"],
    queryFn: () => api.resume.status(),
    refetchInterval: (query) => {
      // Poll every 3s while we're waiting for parse to complete
      if (uploadState === "success" && !query.state.data?.is_parsed) return 3000;
      return false;
    },
  });

  // ── Profile data ──────────────────────────────────────────────
  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: () => api.resume.profile(),
    enabled: parseStatus?.is_parsed === true,
  });

  // ── Upload mutation ───────────────────────────────────────────
  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.resume.upload(file),
    onMutate: () => {
      setUploadState("uploading");
      setErrorMsg("");
    },
    onSuccess: () => {
      setUploadState("success");
      qc.invalidateQueries({ queryKey: ["resume-status"] });
      qc.invalidateQueries({ queryKey: ["profile"] });
    },
    onError: (err: Error) => {
      setUploadState("error");
      setErrorMsg(err.message || "Upload failed. Please try again.");
    },
  });

  const handleFile = useCallback(
    (file: File) => {
      // Validate extension
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (ext !== "pdf" && ext !== "docx") {
        setUploadState("error");
        setErrorMsg("Only PDF and DOCX files are accepted.");
        return;
      }
      // Validate size
      if (file.size > MAX_SIZE) {
        setUploadState("error");
        setErrorMsg("File too large. Maximum size is 5 MB.");
        return;
      }
      uploadMutation.mutate(file);
    },
    [uploadMutation],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset so the same file can be re-selected
    e.target.value = "";
  };

  // ── Render ────────────────────────────────────────────────────
  const isParsed = parseStatus?.is_parsed === true;
  const isProcessing = uploadState === "success" && !isParsed;

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
        className={[
          "relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200",
          dragOver
            ? "border-blue-400 bg-blue-50/50 scale-[1.01]"
            : uploadState === "error"
            ? "border-red-300 bg-red-50/30 hover:border-red-400"
            : "border-gray-200 bg-gray-50/30 hover:border-gray-300 hover:bg-gray-50",
        ].join(" ")}
      >
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPTED}
          onChange={onFileChange}
          className="hidden"
          aria-label="Upload resume"
        />

        {uploadState === "uploading" ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-10 w-10 text-blue-500 animate-spin" />
            <p className="text-sm font-medium text-gray-700">Uploading…</p>
          </div>
        ) : uploadState === "error" ? (
          <div className="flex flex-col items-center gap-3">
            <AlertCircle className="h-10 w-10 text-red-400" />
            <p className="text-sm font-medium text-red-600">{errorMsg}</p>
            <button
              onClick={(e) => { e.stopPropagation(); setUploadState("idle"); setErrorMsg(""); }}
              className="text-xs text-gray-500 hover:text-gray-700 underline"
            >
              Try again
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
              <Upload className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">
                {isParsed ? "Upload a new resume" : "Drop your resume here"}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                PDF or DOCX, max 5 MB
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Processing indicator */}
      {isProcessing && (
        <div className="flex items-center gap-3 rounded-lg bg-blue-50 border border-blue-200 px-4 py-3">
          <Loader2 className="h-4 w-4 text-blue-500 animate-spin flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-blue-700">Parsing your resume…</p>
            <p className="text-xs text-blue-500">
              AI is extracting your skills, experience, and education.
            </p>
          </div>
        </div>
      )}

      {/* Parsed profile summary */}
      {isParsed && profile && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            <h3 className="font-semibold text-sm text-gray-900">
              Resume parsed successfully
            </h3>
          </div>

          {profile.current_title && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Current Title
              </p>
              <p className="text-sm text-gray-900">{profile.current_title}</p>
            </div>
          )}

          {profile.years_experience != null && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Experience
              </p>
              <p className="text-sm text-gray-900">
                {profile.years_experience} {profile.years_experience === 1 ? "year" : "years"}
              </p>
            </div>
          )}

          {profile.skills.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Skills ({profile.skills.length})
              </p>
              <div className="flex flex-wrap gap-1.5">
                {profile.skills.slice(0, 15).map((skill) => (
                  <span
                    key={skill}
                    className="rounded-full bg-blue-50 border border-blue-200 px-2.5 py-0.5 text-xs text-blue-700 font-medium"
                  >
                    {skill}
                  </span>
                ))}
                {profile.skills.length > 15 && (
                  <span className="rounded-full bg-gray-50 border border-gray-200 px-2.5 py-0.5 text-xs text-gray-500">
                    +{profile.skills.length - 15} more
                  </span>
                )}
              </div>
            </div>
          )}

          {profile.has_embedding && (
            <div className="flex items-center gap-2 rounded-lg bg-green-50 border border-green-200 px-3.5 py-2.5">
              <Sparkles className="h-4 w-4 text-green-600" />
              <p className="text-xs text-green-700 font-medium">
                AI matching is active — you'll see match scores on job cards.
              </p>
            </div>
          )}

          {!profile.has_embedding && (
            <div className="flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3.5 py-2.5">
              <Sparkles className="h-4 w-4 text-amber-600" />
              <p className="text-xs text-amber-700 font-medium">
                Embedding is being generated — match scores will appear shortly.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
