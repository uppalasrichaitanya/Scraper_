"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import Link from "next/link";
import type { Application } from "@/lib/types";

interface KanbanCardProps {
  application: Application;
}

export default function KanbanCard({ application }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: application.id });

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
      }}
      className={isDragging ? "opacity-50 z-50" : ""}
    >
      <div className="bg-background border border-border rounded-lg p-3 flex items-start gap-2 shadow-sm cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow">
        <GripVertical
          className="w-4 h-4 mt-0.5 text-muted-foreground flex-shrink-0 touch-none"
          {...attributes}
          {...listeners}
        />
        <div className="flex-1 min-w-0">
          <Link
            href={`/jobs/${application.job_id}`}
            className="text-sm font-medium hover:underline line-clamp-2 block"
            onClick={(e) => e.stopPropagation()}
          >
            {application.job_title ?? "Job"}
          </Link>
          <p className="text-xs text-muted-foreground mt-0.5">
            {application.company_name}
          </p>
          {application.notes && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-1 italic">
              {application.notes}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
