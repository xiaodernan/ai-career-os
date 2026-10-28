import { weightBand } from "@/lib/format";

/**
 * The memory editor's two corrections, kept apart.
 *
 * The endpoint takes `content` and `importance` independently — "fixing the content and
 * lowering the weight are two different corrections" — and an unsent field is left as it
 * was. The card therefore has to send only the correction the reader made.
 *
 * The select shows the band a stored weight falls in, and the bands are wider than the
 * values they map to: 0.7 reads "Normal" and the normal band's canonical weight is 0.6.
 * So an untouched select must send nothing at all — re-sending the band on a text-only
 * edit would quietly rewrite 0.7 to 0.6, a change the reader never asked for. `null` is
 * "the reader never touched the select".
 */

/** The weights the card offers, in the order it lists them. */
export const MEMORY_WEIGHTS = ["0.3", "0.6", "0.9"] as const;

/** The select's value for a stored weight: the canonical number of the band that holds it. */
export function weightValueFor(importance: number): string {
  // weightBand's ladder is exactly low / normal / high; anything not at an edge is normal.
  switch (weightBand(importance)) {
    case "low":
      return "0.3";
    case "high":
      return "0.9";
    default:
      return "0.6";
  }
}

/** The select's value: what the reader picked, or the band that holds the stored weight. */
export function shownWeight(importance: number, picked: string | null): string {
  return picked ?? weightValueFor(importance);
}

/** The PATCH body: the text always, the weight only when the reader moved the select. */
export function memoryPatch(
  id: string,
  draft: string,
  picked: string | null
): { id: string; content: string; importance?: number } {
  return picked === null
    ? { id, content: draft }
    : { id, content: draft, importance: Number(picked) };
}
