import type { Metadata } from "next";
import { LandingPage } from "./landing-page";

/**
 * The public front door: the marketing page (18.2).
 *
 * The signed-in surfaces live under the `(app)` group, which carries the auth
 * guard — so the root is the one page an anonymous visitor can reach, and it
 * links into the product rather than pretending to be it.
 */
export const metadata: Metadata = {
  title: "AI Career OS — your personal job-search operating system",
  description:
    "Evidence-backed matching, resume intelligence, growth planning and AI-guided interviews — every conclusion traced to your own material.",
};

export default function Home() {
  return <LandingPage />;
}
