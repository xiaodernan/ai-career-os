import {
  Briefcase,
  Building2,
  CalendarClock,
  Database,
  FileText,
  Gauge,
  Handshake,
  LayoutDashboard,
  Library,
  Layers,
  MessageSquare,
  Settings,
  Sparkles,
  Activity as ActivityIcon,
  BarChart3,
  TrendingUp,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  description: string;
  /**
   * The translation key for this item's label. The English `label` stays the
   * fallback so the table can be read without a provider mounted, and so a
   * route test can assert a name that does not change with the locale.
   */
  labelKey?: string;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard, description: "Career overview and priorities" },
  { href: "/resumes", label: "Resumes", labelKey: "nav.resumes", icon: FileText, description: "Resume versions and structured profile" },
  { href: "/jobs", label: "Jobs", labelKey: "nav.jobs", icon: Briefcase, description: "Discovered jobs and AI matches" },
  { href: "/applications", label: "Applications", labelKey: "nav.applications", icon: CalendarClock, description: "Pipeline kanban and reminders" },
  { href: "/interviews", label: "Interviews", labelKey: "nav.interviews", icon: Sparkles, description: "Adaptive AI mock interviews" },
  { href: "/copilot", label: "Copilot", labelKey: "nav.copilot", icon: MessageSquare, description: "Career agent conversation" },
  { href: "/knowledge", label: "Knowledge", labelKey: "nav.knowledge", icon: Library, description: "Career knowledge base sources" },
  { href: "/companies", label: "Companies", labelKey: "nav.companies", icon: Building2, description: "Company research profiles" },
  { href: "/growth", label: "Growth", labelKey: "nav.growth", icon: TrendingUp, description: "Readiness, gaps and learning plan" },
  { href: "/networking", label: "Networking", labelKey: "nav.networking", icon: Users, description: "Contacts and outreach" },
  { href: "/analysis", label: "Analysis", labelKey: "nav.analysis", icon: BarChart3, description: "Pipeline analytics and insights" },
  { href: "/offers", label: "Offers", labelKey: "nav.offers", icon: Handshake, description: "Salary benchmarks and negotiation" },
  { href: "/monitoring", label: "Monitoring", labelKey: "nav.monitoring", icon: ActivityIcon, description: "Agent health and cost" },
  { href: "/rate-limit", label: "Rate limit", labelKey: "nav.rateLimit", icon: Gauge, description: "Rate-limit status and quotas" },
  { href: "/ingestion", label: "Ingestion", icon: Layers, description: "Import jobs from feeds and boards" },
  { href: "/data", label: "Your data", icon: Database, description: "Export, restore and redact your data" },
  { href: "/activity", label: "Activity", labelKey: "nav.activity", icon: ActivityIcon, description: "AI agent runs and traces" },
  { href: "/settings", label: "Settings", labelKey: "nav.settings", icon: Settings, description: "Account and preferences" },
];

/**
 * The page title for a pathname.
 *
 * The English label is the answer unless a `translate` is handed in: the
 * function is called from a server component too, where no locale provider is
 * mounted, and a missing provider must not turn the title into a key.
 */
export function titleForPath(pathname: string, translate?: (key: string) => string): string {
  const match = NAV_ITEMS.find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`)
  );
  if (!match) return "AI Career OS";
  if (translate && match.labelKey) {
    const translated = translate(match.labelKey);
    if (translated && translated !== match.labelKey) return translated;
  }
  return match.label;
}
