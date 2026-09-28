"use client";

import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Application, ApplicationStatus } from "@/lib/api/types";
import { STAGE_ORDER, stageMeta, pickerStages } from "@/lib/pipeline";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface KanbanColumnProps {
  status: ApplicationStatus;
  apps: Application[];
  onReorder: (id: string, status: ApplicationStatus, order: number) => void;
  onOpen: (app: Application) => void;
  isPending: boolean;
}

function KanbanColumn({ status, apps, onReorder, onOpen, isPending }: KanbanColumnProps) {
  const meta = stageMeta(status);

  return (
    <div className="flex flex-col min-w-[280px] max-w-[320px] flex-1">
      <div
        className={cn(
          "flex items-center gap-2 px-3 py-2 rounded-t-lg border-b",
          "bg-muted/30"
        )}
      >
        <span className={cn("size-2 rounded-full", meta.dotClass)} aria-hidden />
        <h3 className="font-semibold text-sm">{meta.label}</h3>
        <span className="ml-auto text-xs text-muted-foreground">{apps.length}</span>
      </div>
      <SortableContext
        items={apps.map((a) => a.id)}
        strategy={verticalListSortingStrategy}
      >
        <div
          className="flex-1 flex flex-col gap-2 p-2 min-h-[400px]"
          role="list"
          aria-label={`${meta.label} applications`}
        >
          {apps.map((app, index) => (
            <KanbanCard
              key={app.id}
              app={app}
              index={index}
              status={status}
              isPending={isPending}
              onReorder={onReorder}
              onOpen={onOpen}
            />
          ))}
          {apps.length === 0 && (
            <div
              className="flex-1 flex flex-col items-center justify-center text-muted-foreground/50 text-sm p-4"
              role="status"
            >
              <GripVertical className="size-8 mb-2 opacity-30" aria-hidden />
              <p>Drop here or create new</p>
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

interface KanbanCardProps {
  app: Application;
  index: number;
  status: ApplicationStatus;
  isPending: boolean;
  onReorder: (id: string, status: ApplicationStatus, order: number) => void;
  onOpen: (app: Application) => void;
}

function KanbanCard({
  app,
  index,
  status,
  isPending,
  onReorder,
  onOpen,
}: KanbanCardProps) {
  const meta = stageMeta(app.status);
  const { setNodeRef, setActivatorNodeRef, attributes, listeners, transform, transition, isDragging } =
    useSortable({ id: app.id, data: { currentIndex: index } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  // Radix Select hands over the value, not a change event — the native-select
  // signature would typecheck against nothing and fail at runtime.
  const handleStatusChange = (value: string) => {
    if (value !== status) {
      onReorder(app.id, value as ApplicationStatus, 0);
    }
  };

  return (
    <div
      ref={(el) => {
        setNodeRef(el);
        setActivatorNodeRef(el);
      }}
      style={style}
      className={cn(
        "group relative flex flex-col gap-2 rounded-lg border bg-card p-3 shadow-sm",
        "hover:shadow-md transition-shadow",
        isDragging && "shadow-lg ring-2 ring-primary/20"
      )}
      role="listitem"
      aria-grabbed={isDragging}
    >
      <div className="flex items-start gap-2">
        <div
          {...attributes}
          {...listeners}
          className={cn(
            "flex size-8 shrink-0 items-center justify-center rounded bg-muted text-muted-foreground",
            "hover:bg-muted-foreground/20 active:bg-muted-foreground/30",
            "cursor-grab active:cursor-grabbing",
            isDragging && "bg-primary/10 text-primary"
          )}
          aria-label="Drag to reorder"
        >
          <GripVertical className="size-4" aria-hidden />
        </div>
        <div className="min-w-0 flex-1">
          {/* The card's own fields open the editor; the drag handle beside it stays the only
              drag activator, so a click here is never mistaken for a move. */}
          <button
            type="button"
            onClick={() => onOpen(app)}
            className="block max-w-full truncate text-left text-sm font-medium hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            {app.title}
          </button>
          <p className="truncate text-xs text-muted-foreground">
            {app.company?.name ?? app.companyName}
            {app.reminderAt && (
              <> · reminder {new Date(app.reminderAt).toLocaleDateString()}</>
            )}
          </p>
          {app.note && (
            <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{app.note}</p>
          )}
        </div>
        <Select
          value={app.status}
          onValueChange={handleStatusChange}
          disabled={isPending}
        >
          <SelectTrigger className={cn(
            "w-fit min-w-0",
            "data-[placeholder]:text-muted-foreground"
          )}>
            <SelectValue placeholder={meta.short} />
          </SelectTrigger>
          <SelectContent position="popper">
            {pickerStages(app.status).map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Badge variant={meta.badgeVariant} className="mt-1 w-fit">
        {meta.short}
      </Badge>
    </div>
  );
}

interface KanbanBoardProps {
  applications: Application[];
  onReorder: (id: string, status: ApplicationStatus, order: number) => void;
  /** Opens the editor for a card. The board itself only ever moves them. */
  onOpen: (app: Application) => void;
  isPending: boolean;
}

export function KanbanBoard({ applications, onReorder, onOpen, isPending }: KanbanBoardProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const columns = STAGE_ORDER.map((status) => ({
    status,
    apps: applications
      .filter((a) => a.status === status)
      .sort((a, b) => (a.position ?? 0) - (b.position ?? 0)),
  }));

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    if (activeId === overId) return;

    const activeApp = applications.find((a) => a.id === activeId);
    const overApp = applications.find((a) => a.id === overId);

    if (!activeApp || !overApp) return;

    const activeColumn = columns.find((c) => c.apps.some((a) => a.id === activeId));
    const overColumn = columns.find((c) => c.apps.some((a) => a.id === overId));

    if (!activeColumn || !overColumn) return;

    if (activeColumn.status === overColumn.status) {
      const oldIndex = activeColumn.apps.findIndex((a) => a.id === activeId);
      const newIndex = overColumn.apps.findIndex((a) => a.id === overId);
      const newApps = arrayMove(activeColumn.apps, oldIndex, newIndex);
      newApps.forEach((app, idx) => {
        if (app.position !== idx) {
          onReorder(app.id, overColumn.status, idx);
        }
      });
    } else {
      onReorder(activeId, overColumn.status, overColumn.apps.findIndex((a) => a.id === overId));
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {columns.map(({ status, apps }) => (
          <KanbanColumn
            key={status}
            status={status}
            apps={apps}
            onReorder={onReorder}
            onOpen={onOpen}
            isPending={isPending}
          />
        ))}
      </div>
    </DndContext>
  );
}
