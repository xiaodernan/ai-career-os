import {
  Bell,
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
   *
   * It is *required*, and that is the point. An item without one renders its
   * English name on every language, and the reader has no way to tell that
   * is what happened -- it looks like an untranslated product. Two items were
   * exactly that for a while, and the gate that claims to catch it was
   * checking the table's keys rather than the table's items, so it never
   * looked at them. Making the key required moves the check into the type
   * checker, where it cannot be forgotten.
   */
  labelKey: string;
  /**
   * The translation key for this item's description.
   *
   * The description is the second line of the command palette's row -- the
   * sentence that says what the page is for -- and it was the English one on
   * every language, because it was a plain string in a table nobody had
   * given a key. Required for the same reason `labelKey` is: a word the
   * reader cannot change is a word the reader cannot have.
   */
  descriptionKey: string;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", labelKey: "nav.dashboard", descriptionKey: "navDescriptions.dashboard", icon: LayoutDashboard, description: "Career overview and priorities" },
  { href: "/notifications", label: "Notifications", labelKey: "nav.notifications", descriptionKey: "navDescriptions.notifications", icon: Bell, description: "Signals that need your attention" },
  { href: "/resumes", label: "Resumes", labelKey: "nav.resumes", descriptionKey: "navDescriptions.resumes", icon: FileText, description: "Resume versions and structured profile" },
  { href: "/jobs", label: "Jobs", labelKey: "nav.jobs", descriptionKey: "navDescriptions.jobs", icon: Briefcase, description: "Discovered jobs and AI matches" },
  { href: "/applications", label: "Applications", labelKey: "nav.applications", descriptionKey: "navDescriptions.applications", icon: CalendarClock, description: "Pipeline kanban and reminders" },
  { href: "/interviews", label: "Interviews", labelKey: "nav.interviews", descriptionKey: "navDescriptions.interviews", icon: Sparkles, description: "Adaptive AI mock interviews" },
  { href: "/copilot", label: "Copilot", labelKey: "nav.copilot", descriptionKey: "navDescriptions.copilot", icon: MessageSquare, description: "Career agent conversation" },
  { href: "/knowledge", label: "Knowledge", labelKey: "nav.knowledge", descriptionKey: "navDescriptions.knowledge", icon: Library, description: "Career knowledge base sources" },
  { href: "/companies", label: "Companies", labelKey: "nav.companies", descriptionKey: "navDescriptions.companies", icon: Building2, description: "Company research profiles" },
  { href: "/growth", label: "Growth", labelKey: "nav.growth", descriptionKey: "navDescriptions.growth", icon: TrendingUp, description: "Readiness, gaps and learning plan" },
  { href: "/networking", label: "Networking", labelKey: "nav.networking", descriptionKey: "navDescriptions.networking", icon: Users, description: "Contacts and outreach" },
  { href: "/analysis", label: "Analysis", labelKey: "nav.analysis", descriptionKey: "navDescriptions.analysis", icon: BarChart3, description: "Pipeline analytics and insights" },
  { href: "/offers", label: "Offers", labelKey: "nav.offers", descriptionKey: "navDescriptions.offers", icon: Handshake, description: "Salary benchmarks and negotiation" },
  { href: "/monitoring", label: "Monitoring", labelKey: "nav.monitoring", descriptionKey: "navDescriptions.monitoring", icon: ActivityIcon, description: "Agent health and cost" },
  { href: "/rate-limit", label: "Rate limit", labelKey: "nav.rateLimit", descriptionKey: "navDescriptions.rateLimit", icon: Gauge, description: "Rate-limit status and quotas" },
  { href: "/ingestion", label: "Ingestion", labelKey: "nav.ingestion", descriptionKey: "navDescriptions.ingestion", icon: Layers, description: "Import jobs from feeds and boards" },
  { href: "/data", label: "Your data", labelKey: "nav.yourData", descriptionKey: "navDescriptions.yourData", icon: Database, description: "Export, restore and redact your data" },
  { href: "/activity", label: "Activity", labelKey: "nav.activity", descriptionKey: "navDescriptions.activity", icon: ActivityIcon, description: "AI agent runs and traces" },
  { href: "/settings", label: "Settings", labelKey: "nav.settings", descriptionKey: "navDescriptions.settings", icon: Settings, description: "Account and preferences" },
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

/**
 * The public routes' own titles.
 *
 * These are not in the navigation -- a visitor who has not signed in has no
 * sidebar -- but they are pages the reader can be on, and their title is
 * the same word in the same place as every other page's.
 *
 * The table is here rather than in a route file because the title is
 * rendered by the server, and the server reads the locale out of the
 * cookie the browser writes -- see `lib/i18n/metadata.ts`.
 */
export const PUBLIC_PAGE_TITLES: Record<string, { key: string; label: string }> = {
  "/": {
    key: "landing.pageTitle",
    label: "AI Career OS — your personal job-search operating system",
  },
  "/login": { key: "auth.pageTitles.signIn", label: "Sign in" },
  "/register": { key: "auth.pageTitles.signUp", label: "Create account" },
  "/forgot-password": {
    key: "auth.pageTitles.forgotPassword",
    label: "Reset your password",
  },
  "/reset-password": {
    key: "auth.pageTitles.resetPassword",
    label: "Set a new password",
  },
};
