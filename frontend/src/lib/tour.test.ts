import { describe, expect, it } from "vitest";
import {
  TOUR_HREFS,
  clearTourVisits,
  markTourVisited,
  readTourVisits,
  tourProgress,
} from "./tour";

function memoryStorage(seed?: string) {
  const map = new Map<string, string>();
  if (seed) map.set("careeros.tour.v1", seed);
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  } as unknown as Storage;
}

describe("the nine quests", () => {
  it("nine rooms, same order the landing map draws", () => {
    expect(TOUR_HREFS).toEqual([
      "/resumes",
      "/studio",
      "/growth",
      "/letters",
      "/interviews",
      "/applications",
      "/replies",
      "/offers",
      "/ceremony",
    ]);
  });

  it("marking a room checked persists it; unknown routes are ignored", () => {
    const storage = memoryStorage();
    expect(markTourVisited("/settings", storage)).toEqual([]);
    markTourVisited("/resumes", storage);
    markTourVisited("/offers", storage);
    expect(readTourVisits(storage).sort()).toEqual(["/offers", "/resumes"]);
    markTourVisited("/resumes", storage);
    expect(readTourVisits(storage)).toHaveLength(2);
  });

  it("reads only the routes that belong to the tour; garbage is dropped", () => {
    const storage = memoryStorage(
      JSON.stringify({ visited: ["/resumes", "/nowhere", 42, "/offers", "/resumes"] })
    );
    expect(readTourVisits(storage).sort()).toEqual(["/offers", "/resumes"]);
  });

  it("a corrupt blob reads as the empty tour, not a crash", () => {
    expect(readTourVisits(memoryStorage("nope {"))).toEqual([]);
    expect(readTourVisits(memoryStorage(JSON.stringify({ visited: "nope" })))).toEqual([]);
  });

  it("progress counts known rooms only and clears cleanly", () => {
    expect(tourProgress(["/resumes", "/offers", "/settings"])).toEqual({ done: 2, total: 9 });
    expect(tourProgress([])).toEqual({ done: 0, total: 9 });
    const storage = memoryStorage();
    markTourVisited("/ceremony", storage);
    clearTourVisits(storage);
    expect(readTourVisits(storage)).toEqual([]);
  });
});
