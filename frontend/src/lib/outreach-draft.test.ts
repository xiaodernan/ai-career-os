import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import type { OutreachDraft } from "@/lib/api/types";

/**
 * The outreach draft's field names, end to end.
 *
 * The engine answers with `subject`, `body`, `contactName`, `purpose`,
 * `evidenceUsed` and `allowedEvidence` -- and the page used to read a
 * `message` field the engine has never sent. The draft was written, the
 * audit run recorded it, the cost was billed, and the screen showed
 * nothing at all: a blank space where a message to a person should have
 * been.
 *
 * The gap was invisible in the type system, because the type said
 * `message?: string` and the page read `draft.data?.message` -- two
 * halves of the same wrong name, agreeing with each other and with
 * neither the engine. So the gate here reads the engine's own shape
 * (the ai-service's `features/outreach.py::compose`) and the page's, and
 * holds the two to the same names.
 */

const PAGE = fileURLToPath(new URL("../app/(app)/networking/page.tsx", import.meta.url));
const ENGINE = fileURLToPath(
  new URL("../../../ai-service/app/features/outreach.py", import.meta.url)
);

describe("the outreach draft's field names", () => {
  const page = readFileSync(PAGE, "utf-8");
  const engine = readFileSync(ENGINE, "utf-8");

  it("the engine answers with a body, a subject and the evidence it cited", () => {
    // The engine's own `compose` is the shape of record: these are the
    // names it writes.
    for (const field of ["subject", "body", "contactName", "evidenceUsed", "allowedEvidence"]) {
      expect(engine, `the engine no longer answers with ${field}`).toContain(
        `"${field}":`
      );
    }
  });

  it("the page reads the names the engine writes", () => {
    // The page must not read a field the engine does not send, and it
    // must read the one that carries the message.
    expect(page, "the page does not read the drafted body").toContain("draft.data.body");
    expect(page, "the page reads a field the engine never sends").not.toContain(
      "draft.data?.message"
    );
  });

  it("the type carries the engine's names and no others", () => {
    // The type is what let the two halves agree on the wrong name.
    const draft: OutreachDraft = {
      subject: "A quick question",
      body: "Hi — I am a backend engineer...",
      contactName: "Ada Lovelace",
      purpose: "referral",
      evidenceUsed: ["Java"],
      allowedEvidence: ["Java", "Spring Boot"],
    };
    expect(draft.body).toBeTruthy();
    // And it does not carry a `message` any more, so a page that reaches
    // for one does not compile.
    const type = readFileSync(
      fileURLToPath(new URL("./api/types.ts", import.meta.url)),
      "utf-8"
    );
    const block = type.slice(type.indexOf("export interface OutreachDraft"));
    expect(block.slice(0, block.indexOf("}"))).not.toContain("message?:");
  });
});
