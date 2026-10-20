import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Briefcase,
  CheckCircle2,
  FileText,
  MessageSquare,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/**
 * The marketing landing page (18.2): a public-facing page that introduces
 * AI Career OS and links to the app.
 */
export function LandingPage() {
  return (
    <div className="min-h-dvh bg-background">
      {/* Header */}
      <header className="border-b border-border/50">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="size-4" aria-hidden />
            </span>
            <span className="font-serif text-lg font-semibold tracking-tight">
              Career<span className="text-primary">OS</span>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/auth/login">Sign in</Link>
            </Button>
            <Button variant="ai" size="sm" asChild>
              <Link href="/auth/register">
                Get started
                <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 py-20 text-center">
        <div className="mx-auto max-w-3xl">
          <h1 className="font-serif text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
            Your personal
            <span className="text-primary"> job-search</span>
            <br />
            operating system
          </h1>
          <p className="mt-6 text-lg text-muted-foreground">
            AI Career OS turns your resume, the job market, and a fleet of AI agents
            into one evidence-backed system — from resume → knowledge base → job
            discovery → matching → tailored materials → mock interviews → application
            tracking.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Button variant="ai" size="lg" asChild>
              <Link href="/auth/register">
                Start free
                <ArrowRight className="size-4" aria-hidden />
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/auth/login">Sign in</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border/50 bg-muted/30">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <h2 className="text-center font-serif text-3xl font-semibold tracking-tight">
            Everything you need
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-center text-muted-foreground">
            One system for your entire job search — every AI conclusion is traceable
            to your own material.
          </p>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={<FileText className="size-5" aria-hidden />}
              title="Resume Intelligence"
              description="Upload PDF/DOCX/TXT → parse → structured profile + versioned resumes with live score."
            />
            <FeatureCard
              icon={<Target className="size-5" aria-hidden />}
              title="JD Analysis & Matching"
              description="Requirements/skills/interview topics extracted; deterministic match scores bound to resume evidence."
            />
            <FeatureCard
              icon={<MessageSquare className="size-5" aria-hidden />}
              title="Adaptive Mock Interviews"
              description="Interviewer agent that drills, follows up and scales difficulty; 8-dimension report + depth trajectory."
            />
            <FeatureCard
              icon={<Briefcase className="size-5" aria-hidden />}
              title="Application Tracker"
              description="Linear-style kanban with transition audit events — saved → applied → OA → interview → offer."
            />
            <FeatureCard
              icon={<TrendingUp className="size-5" aria-hidden />}
              title="Growth Intelligence"
              description="Gap analysis, learning plans, salary benchmarks, and career progression planning."
            />
            <FeatureCard
              icon={<BarChart3 className="size-5" aria-hidden />}
              title="Analytics & Insights"
              description="Pipeline funnel, response rates, stalled applications, and weekly insight digests."
            />
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="border-t border-border/50">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <div className="grid gap-8 sm:grid-cols-3">
            <TrustItem
              icon={<Shield className="size-5" aria-hidden />}
              title="Evidence-bound"
              description="Every AI claim traces to your own material — no fabrication, no invented experience."
            />
            <TrustItem
              icon={<Users className="size-5" aria-hidden />}
              title="User-scoped"
              description="Your data is yours. Every query is scoped to your user id — no cross-user leakage."
            />
            <TrustItem
              icon={<CheckCircle2 className="size-5" aria-hidden />}
              title="Inspectable"
              description="Every agent run is recorded: traces, tool calls, retrieval, tokens, cost."
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border/50 bg-primary/5">
        <div className="mx-auto max-w-6xl px-4 py-20 text-center">
          <h2 className="font-serif text-3xl font-semibold tracking-tight">
            Ready to build your career OS?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Start with your resume — the system builds your knowledge base, finds
            matching jobs, and prepares you for interviews.
          </p>
          <div className="mt-8">
            <Button variant="ai" size="lg" asChild>
              <Link href="/auth/register">
                Get started free
                <ArrowRight className="size-4" aria-hidden />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 text-sm text-muted-foreground">
          <span>© 2026 AI Career OS</span>
          <span>Personal project, active development</span>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </span>
        <h3 className="mt-4 font-semibold">{title}</h3>
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}

function TrustItem({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="text-center">
      <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
        {icon}
      </span>
      <h3 className="mt-4 font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
