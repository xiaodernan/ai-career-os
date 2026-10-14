import {
  Briefcase,
  Building2,
  CalendarClock,
  FileText,
  LayoutDashboard,
  Library,
  MessageSquare,
  Settings,
  Sparkles,
  Activity as ActivityIcon,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, description: "Career overview and priorities" },
  { href: "/resumes", label: "Resumes", icon: FileText, description: "Resume versions and structured profile" },
  { href: "/jobs", label: "Jobs", icon: Briefcase, description: "Discovered jobs and AI matches" },
  { href: "/applications", label: "Applications", icon: CalendarClock, description: "Pipeline kanban and reminders" },
  { href: "/interviews", label: "Interviews", icon: Sparkles, description: "Adaptive AI mock interviews" },
  { href: "/copilot", label: "Copilot", icon: MessageSquare, description: "Career agent conversation" },
  { href: "/knowledge", label: "Knowledge", icon: Library, description: "Career knowledge base sources" },
  { href: "/companies", label: "Companies", icon: Building2, description: "Company research profiles" },
  { href: "/growth", label: "Growth", icon: TrendingUp, description: "Readiness, gaps and learning plan" },
  { href: "/activity", label: "Activity", icon: ActivityIcon, description: "AI agent runs and traces" },
  { href: "/settings", label: "Settings", icon: Settings, description: "Account and preferences" },
];

export function titleForPath(pathname: string): string {
  const match = NAV_ITEMS.find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`)
  );
  return match?.label ?? "AI Career OS";
}
