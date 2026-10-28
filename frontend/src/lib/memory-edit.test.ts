import { describe, expect, it } from "vitest";

import { WEIGHTS } from "@/components/settings/memory-card";
import { MEMORY_WEIGHTS, memoryPatch, shownWeight, weightValueFor } from "./memory-edit";

/**
 * What the memory editor puts on the wire when the reader saves.
 *
 * The endpoint takes `content` and `importance` independently, and a field that is not sent
 * is left alone. The editor used to always send both: the select was initialized with the
 * stored weight's *band* (`Normal`), and saving mapped that band back to its canonical
 * number (0.6) — so fixing a memory's text silently rewrote a stored 0.7 to 0.6. The two
 * facts a reader can correct have to stay two facts.
 */

describe("the memory editor's PATCH body", () => {
  it("sends only the text when the reader did not move the select", () => {
    const body = memoryPatch("m1", "Prefers backend roles.", null);
    expect(body).toEqual({ id: "m1", content: "Prefers backend roles." });
    // Absent, not undefined: a key that is present is a key the next caller can fill in.
    expect(Object.keys(body)).toEqual(["id", "content"]);
  });

  it("sends the weight the reader picked, as the number the endpoint takes", () => {
    expect(memoryPatch("m1", "x", "0.3")).toEqual({ id: "m1", content: "x", importance: 0.3 });
    expect(memoryPatch("m1", "x", "0.6").importance).toBe(0.6);
    expect(memoryPatch("m1", "x", "0.9").importance).toBe(0.9);
  });
});

describe("the card's options and this module's ladder", () => {
  it("offer exactly the values the band mapping returns", () => {
    // The mapping returns a value; the select has to have an item for it. The card owns the
    // labels (they are copy the census reads), so the two lists are held together here.
    expect(WEIGHTS.map((w) => w.value)).toEqual([...MEMORY_WEIGHTS]);
  });
});

describe("the weight select's value", () => {
  it("shows a stored weight as the band that holds it, from the offered ladder", () => {
    // weightLabel's pinned boundaries: <=0.35 Low, >=0.85 High, the rest Normal.
    for (const importance of [0, 0.1, 0.35, 0.36, 0.6, 0.84, 0.85, 1]) {
      expect(MEMORY_WEIGHTS as readonly string[]).toContain(weightValueFor(importance));
    }
    expect(weightValueFor(0.1)).toBe("0.3");
    expect(weightValueFor(0.6)).toBe("0.6");
    expect(weightValueFor(0.9)).toBe("0.9");
  });

  it("gives the three bands three different values, so the select can tell them apart", () => {
    const values = new Set([weightValueFor(0.1), weightValueFor(0.6), weightValueFor(0.9)]);
    expect(values.size, "two bands mapped to one value would make the select lie").toBe(3);
  });

  it("shows the reader's pick over the stored band", () => {
    expect(shownWeight(0.7, null)).toBe("0.6");
    expect(shownWeight(0.7, "0.9")).toBe("0.9");
  });

  it("leaves a stored 0.7 at 0.7 when only the text is edited", () => {
    // The bug this file exists for: the select says "Normal" because 0.7 is in that band,
    // and the save must still send *nothing* about the weight.
    expect(shownWeight(0.7, null)).toBe("0.6");
    expect(memoryPatch("m1", "a corrected sentence", null)).not.toHaveProperty("importance");
  });
});
