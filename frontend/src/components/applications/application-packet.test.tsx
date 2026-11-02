import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type * as React from "react";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string) => key, setLocale: () => {} }),
}));

import { ApplicationPacketPanel } from "./application-packet";
import type { Application, ApplicationPacket } from "@/lib/api/types";

const application: Application = {
  id: "app-1",
  title: "Staff Backend Engineer",
  status: "applied",
};

const full: ApplicationPacket = {
  applicationId: "app-1",
  resumeLinked: true,
  resume: {
    id: "rv-1",
    resumeId: "resume-1",
    title: "Ada Lovelace resume",
    label: "Tailored for Northwind",
    kind: "tailored",
    createdAt: "2026-10-01T09:00:00Z",
  },
  jdLinked: true,
  jd: {
    id: "jd-1",
    jobId: "job-1",
    title: "Backend Platform Engineer",
    companyName: "Northwind Labs",
    createdAt: "2026-10-02T09:00:00Z",
  },
  matchLinked: true,
  match: { id: "match-1", jobId: "job-1", overall: 0.82, createdAt: "2026-10-03T09:00:00Z" },
  letters: 2,
};

const render = (props: React.ComponentProps<typeof ApplicationPacketPanel>) =>
  renderToStaticMarkup(<ApplicationPacketPanel {...props} />);

describe("ApplicationPacketPanel", () => {
  it("names every artifact and links it to the screen that owns it", () => {
    const html = render({ application, packet: full });
    expect(html).toContain("Ada Lovelace resume");
    expect(html).toContain("Tailored for Northwind");
    expect(html).toContain("Backend Platform Engineer");
    expect(html).toContain("Northwind Labs");
    expect(html).toContain('href="/resumes/resume-1"');
    expect(html).toContain('href="/jobs/job-1"');
    expect(html).toContain("applications.dialog.packet.letterCount");
  });

  it("keeps an attached-but-unreadable row apart from an empty column", () => {
    const html = render({
      application,
      packet: {
        applicationId: "app-1",
        resumeLinked: true,
        resume: null,
        jdLinked: false,
        jd: null,
        matchLinked: true,
        match: null,
        letters: 0,
      },
    });
    expect(html).toContain("applications.dialog.packet.unavailable");
    expect(html).toContain("applications.dialog.packet.notLinked");
    expect(html).not.toContain('href="/resumes/');
  });

  it("says the packet is empty only when no artifact is linked", () => {
    const html = render({
      application,
      packet: {
        applicationId: "app-1",
        resumeLinked: false,
        resume: null,
        jdLinked: false,
        jd: null,
        matchLinked: false,
        match: null,
        letters: 0,
      },
    });
    expect(html).toContain("applications.dialog.packet.empty");
    expect(html.match(/applications\.dialog\.packet\.notLinked/g)?.length).toBe(3);
    expect(html.match(/applications\.dialog\.packet\.noLetters/g)?.length).toBe(1);
  });

  it("does not call a packet empty when only a letter is kept", () => {
    const html = render({
      application,
      packet: {
        applicationId: "app-1",
        resumeLinked: false,
        resume: null,
        jdLinked: false,
        jd: null,
        matchLinked: false,
        match: null,
        letters: 1,
      },
    });
    expect(html).not.toContain("applications.dialog.packet.empty");
    expect(html).toContain("applications.dialog.packet.letterCount");
  });

  it("shows a loading state without drawing empty rows", () => {
    const html = render({ application, loading: true });
    expect(html).toContain("applications.dialog.packet.loading");
    expect(html).not.toContain("applications.dialog.packet.notLinked");
  });

  it("shows a failed read as a sentence rather than an empty packet", () => {
    const html = render({ application, failed: true });
    expect(html).toContain("applications.dialog.packet.failed");
    expect(html).not.toContain("applications.dialog.packet.empty");
  });
});
