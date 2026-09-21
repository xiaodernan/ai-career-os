import type { ApplicationStatus } from "@/lib/api/types";

/**
 * The frozen pipeline taxonomy shared by the applications kanban, the
 * dashboard mini-board and status pickers. Order here is the board order and
 * doubles as the default column arrangement for optimistic moves.
 */
export interface StageMeta {
  value: ApplicationStatus;
  label: string;
  short: string;
  /** Tailwind classes for the column header dot / accent rail. */
  dotClass: string;
  badgeVariant: "secondary" | "ai" | "warning" | "success" | "destructive" | "outline";
  /** Optimistic UI copy shown in the drawer's status control. */
  blurb: string;
}

export const APPLICATION_STAGES: { value: ApplicationStatus; label: string }[] = [
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "oa", label: "Online assessment" },
  { value: "interview", label: "Interview" },
  { value: "final_round", label: "Final round" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
];

const STAGE_META: Record<ApplicationStatus, StageMeta> = {
  saved: {
    value: "saved",
    label: "Saved",
    short: "Saved",
    dotClass: "bg-muted-foreground/40",
    badgeVariant: "secondary",
    blurb: "Bookmark kept from the job board.",
  },
  applied: {
    value: "applied",
    label: "Applied",
    short: "Applied",
    dotClass: "bg-primary",
    badgeVariant: "ai",
    blurb: "Application submitted.",
  },
  oa: {
    value: "oa",
    label: "Online assessment",
    short: "OA",
    dotClass: "bg-primary/70",
    badgeVariant: "ai",
    blurb: "Awaiting or completing an online test.",
  },
  interview: {
    value: "interview",
    label: "Interview",
    short: "Interview",
    dotClass: "bg-warning",
    badgeVariant: "warning",
    blurb: "In the interview loop.",
  },
  final_round: {
    value: "final_round",
    label: "Final round",
    short: "Final",
    dotClass: "bg-warning/80",
    badgeVariant: "warning",
    blurb: "Last-stage onsite / panel.",
  },
  offer: {
    value: "offer",
    label: "Offer",
    short: "Offer",
    dotClass: "bg-success",
    badgeVariant: "success",
    blurb: "Offer extended — decide or negotiate.",
  },
  rejected: {
    value: "rejected",
    label: "Rejected",
    short: "Rejected",
    dotClass: "bg-destructive",
    badgeVariant: "destructive",
    blurb: "Closed out. Kept for retro analysis.",
  },
};

export function stageMeta(status: string): StageMeta {
  return STAGE_META[status as ApplicationStatus] ?? {
    value: "saved",
    label: status || "Unknown",
    short: status || "?",
    dotClass: "bg-muted-foreground/40",
    badgeVariant: "outline",
    blurb: "",
  };
}

export const STAGE_ORDER: ApplicationStatus[] = APPLICATION_STAGES.map((s) => s.value);

export function isTerminal(status: string): boolean {
  return status === "offer" || status === "rejected";
}
