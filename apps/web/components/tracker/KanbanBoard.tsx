"use client";

import {
  DndContext,
  type DragEndEvent,
  type DragStartEvent,
  type DragOverEvent,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
  closestCenter,
  useDroppable,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { SavedJobItem, SavedJobStatus } from "@/lib/types";
import KanbanCard from "./KanbanCard";

// ── Column definitions with user-specified colours ───────────────────
const COLUMNS: {
  id: SavedJobStatus;
  label: string;
  bg: string;
  border: string;
  dot: string;
}[] = [
  { id: "saved",        label: "Saved",        bg: "bg-gray-50",    border: "border-gray-200",  dot: "bg-gray-400"   },
  { id: "applied",      label: "Applied",      bg: "bg-blue-50",    border: "border-blue-200",  dot: "bg-blue-500"   },
  { id: "interviewing", label: "Interviewing",  bg: "bg-yellow-50",  border: "border-yellow-200", dot: "bg-yellow-500" },
  { id: "offered",      label: "Offered",      bg: "bg-green-50",   border: "border-green-200", dot: "bg-green-500"  },
  { id: "rejected",     label: "Rejected",     bg: "bg-red-50",     border: "border-red-200",   dot: "bg-red-400"    },
];

const COLUMN_IDS = COLUMNS.map((c) => c.id);

// ── Accessibility announcements ──────────────────────────────────────
const announcements = {
  onDragStart: ({ active }: DragStartEvent) =>
    `Picked up job card ${active.id}.`,
  onDragOver: ({ over }: DragOverEvent) =>
    over ? `Moving to ${over.id} column.` : undefined,
  onDragEnd: ({ over }: DragEndEvent) =>
    over ? `Dropped in ${over.id}.` : `Cancelled.`,
  onDragCancel: () => `Drag cancelled.`,
};

// ── Droppable column wrapper ─────────────────────────────────────────
function DroppableColumn({
  column,
  children,
  activeColumnId,
}: {
  column: (typeof COLUMNS)[number];
  children: React.ReactNode;
  activeColumnId: string | null;
}) {
  const { isOver, setNodeRef } = useDroppable({ id: column.id });

  const isDropTarget = isOver && activeColumnId !== column.id;

  return (
    <div
      ref={setNodeRef}
      className={[
        "flex-shrink-0 w-64 rounded-xl p-3 border transition-all duration-200",
        column.bg,
        column.border,
        isDropTarget
          ? "ring-2 ring-blue-400 ring-offset-2 scale-[1.01]"
          : "",
      ].join(" ")}
    >
      {children}
    </div>
  );
}

// ── Main Kanban Board ────────────────────────────────────────────────
export default function KanbanBoard() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeColumnId, setActiveColumnId] = useState<string | null>(null);

  // 8px of pointer movement before drag starts — prevents accidental drags on click
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const { data, isLoading } = useQuery({
    queryKey: ["saved-jobs"],
    queryFn: () => api.savedJobs.list(),
  });

  const savedJobs = data?.items ?? [];

  const updateMutation = useMutation({
    mutationFn: ({ jobId, status }: { jobId: string; status: SavedJobStatus }) =>
      api.savedJobs.updateStatus(jobId, { status }),
    onMutate: async ({ jobId, status }) => {
      await qc.cancelQueries({ queryKey: ["saved-jobs"] });
      const prev = qc.getQueryData<{ total: number; items: SavedJobItem[] }>(["saved-jobs"]);
      qc.setQueryData<{ total: number; items: SavedJobItem[] }>(["saved-jobs"], (old) => {
        if (!old) return old;
        return {
          ...old,
          items: old.items.map((item) =>
            item.job_id === jobId ? { ...item, status } : item,
          ),
        };
      });
      return { prev };
    },
    onError: (_, __, ctx) => {
      if (ctx?.prev) qc.setQueryData(["saved-jobs"], ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["saved-jobs"] }),
  });

  function handleDragStart(event: DragStartEvent) {
    const id = String(event.active.id);
    setActiveId(id);
    // Find which column the dragged item is currently in
    const item = savedJobs.find((sj) => sj.id === id);
    setActiveColumnId(item?.status ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);
    setActiveColumnId(null);

    if (!over) return;

    const newStatus = over.id as SavedJobStatus;
    if (!(COLUMN_IDS as readonly string[]).includes(newStatus)) return;

    const item = savedJobs.find((sj) => sj.id === String(active.id));
    if (!item || item.status === newStatus) return;

    updateMutation.mutate({ jobId: item.job_id, status: newStatus });
  }

  const activeItem = savedJobs.find((sj) => sj.id === activeId);

  if (isLoading) {
    return (
      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((col) => (
          <div
            key={col.id}
            className={`flex-shrink-0 w-64 h-48 rounded-xl border animate-pulse ${col.bg} ${col.border}`}
          />
        ))}
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      accessibility={{ announcements }}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((col) => {
          const cards = savedJobs.filter((sj) => sj.status === col.id);
          return (
            <DroppableColumn
              key={col.id}
              column={col}
              activeColumnId={activeColumnId}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`inline-block h-2.5 w-2.5 rounded-full ${col.dot}`} />
                  <h3 className="font-semibold text-sm">{col.label}</h3>
                </div>
                <span className="text-xs text-muted-foreground bg-background/70 rounded-full px-2 py-0.5 font-medium">
                  {cards.length}
                </span>
              </div>
              <SortableContext
                items={cards.map((c) => c.id)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-2 min-h-[80px]">
                  {cards.map((sj) => (
                    <KanbanCard key={sj.id} savedJob={sj} />
                  ))}
                  {cards.length === 0 && (
                    <div className="border-2 border-dashed border-border/50 rounded-lg h-20 flex items-center justify-center text-xs text-muted-foreground">
                      Drop here
                    </div>
                  )}
                </div>
              </SortableContext>
            </DroppableColumn>
          );
        })}
      </div>

      <DragOverlay>
        {activeItem ? (
          <KanbanCard savedJob={activeItem} isOverlay />
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
