"use client";

import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
  closestCenter,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Application } from "@/lib/types";
import KanbanCard from "./KanbanCard";

const COLUMNS = [
  "saved",
  "applied",
  "interview",
  "offer",
  "rejected",
] as const;
type Status = (typeof COLUMNS)[number];

const COLUMN_LABELS: Record<Status, string> = {
  saved: "💾 Saved",
  applied: "📤 Applied",
  interview: "🎤 Interview",
  offer: "🎉 Offer",
  rejected: "❌ Rejected",
};

const COLUMN_COLORS: Record<Status, string> = {
  saved: "bg-slate-100 dark:bg-slate-800/60",
  applied: "bg-blue-50 dark:bg-blue-950/40",
  interview: "bg-amber-50 dark:bg-amber-950/40",
  offer: "bg-green-50 dark:bg-green-950/40",
  rejected: "bg-red-50 dark:bg-red-950/40",
};

export default function KanbanBoard() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);

  // 8px of pointer movement before drag starts — prevents accidental drags on click
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const { data: applications = [], isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: api.applications.list,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Status }) =>
      api.applications.update(id, { status }),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: ["applications"] });
      const prev = qc.getQueryData<Application[]>(["applications"]);
      qc.setQueryData<Application[]>(["applications"], (old = []) =>
        old.map((a) => (a.id === id ? { ...a, status } : a)),
      );
      return { prev };
    },
    onError: (_, __, ctx) => {
      if (ctx?.prev) qc.setQueryData(["applications"], ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);
    if (!over || active.id === over.id) return;

    // The column droppable zones use the column status string as their ID
    const newStatus = over.id as Status;
    if ((COLUMNS as readonly string[]).includes(newStatus)) {
      updateMutation.mutate({ id: String(active.id), status: newStatus });
    }
  }

  const activeApplication = applications.find((a) => a.id === activeId);

  if (isLoading) {
    return (
      <div className="flex gap-4">
        {COLUMNS.map((col) => (
          <div
            key={col}
            className="flex-shrink-0 w-64 h-48 rounded-lg bg-muted animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={(e) => setActiveId(String(e.active.id))}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((col) => {
          const cards = applications.filter((a) => a.status === col);
          return (
            <div
              key={col}
              id={col}
              className={`flex-shrink-0 w-64 rounded-xl p-3 ${COLUMN_COLORS[col]}`}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-sm">{COLUMN_LABELS[col]}</h3>
                <span className="text-xs text-muted-foreground bg-background/70 rounded-full px-2 py-0.5 font-medium">
                  {cards.length}
                </span>
              </div>
              <SortableContext
                items={cards.map((c) => c.id)}
                strategy={verticalListSortingStrategy}
              >
                {/* The droppable column zone must have the column id */}
                <div className="space-y-2 min-h-[80px]">
                  {cards.map((app) => (
                    <KanbanCard key={app.id} application={app} />
                  ))}
                  {cards.length === 0 && (
                    <div className="border-2 border-dashed border-border/50 rounded-lg h-20 flex items-center justify-center text-xs text-muted-foreground">
                      Drop here
                    </div>
                  )}
                </div>
              </SortableContext>
            </div>
          );
        })}
      </div>

      <DragOverlay>
        {activeApplication ? (
          <KanbanCard application={activeApplication} />
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
