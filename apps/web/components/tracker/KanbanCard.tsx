"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import Link from "next/link";
import type { SavedJobItem } from "@/lib/types";

interface KanbanCardProps {
  savedJob: SavedJobItem;
  /** True when rendering inside the DragOverlay */
  isOverlay?: boolean;
}

export default function KanbanCard({ savedJob, isOverlay = false }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: savedJob.id });

  const job = savedJob.job;

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
      }}
      className={[
        isDragging && !isOverlay ? "opacity-50 scale-95" : "",
        isOverlay ? "rotate-2 shadow-xl" : "",
      ].join(" ")}
    >
      <div
        className={[
          "bg-white border border-gray-200 rounded-xl p-3 flex items-start gap-2 shadow-sm",
          "cursor-grab active:cursor-grabbing",
          "hover:shadow-md transition-all duration-150",
        ].join(" ")}
      >
        <GripVertical
          className="w-4 h-4 mt-0.5 text-muted-foreground flex-shrink-0 touch-none"
          {...attributes}
          {...listeners}
        />
        <div className="flex-1 min-w-0">
          <Link
            href={`/jobs/${savedJob.job_id}`}
            className="text-sm font-medium hover:underline line-clamp-2 block text-gray-900"
            onClick={(e) => e.stopPropagation()}
          >
            {job?.title ?? "Job"}
          </Link>
          <p className="text-xs text-muted-foreground mt-0.5">
            {job?.company_name ?? "Unknown company"}
          </p>
          {job?.location_city && (
            <p className="text-[11px] text-muted-foreground mt-0.5">
              📍 {job.location_city}
            </p>
          )}
          {savedJob.note && (
            <p className="text-xs text-muted-foreground mt-1.5 line-clamp-1 italic border-t border-gray-100 pt-1.5">
              {savedJob.note}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
