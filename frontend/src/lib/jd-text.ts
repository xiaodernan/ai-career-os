/**
 * The floor on a pasted job posting, and the one place the client writes its number.
 *
 * One piece of user text feeds three ai-service requests: `POST /jd/analyze` (`JdReq.raw_text`),
 * `POST /jd/suggestions` (`SuggestReq.jd_raw`) and `POST /resume/parse` (`ParseReq.text`). Each of
 * those declares its own sanity bound, `Field(min_length = 20)`, and the screens deliberately ask
 * for more than the API will accept. Twenty characters clears a Pydantic check without carrying a
 * single requirement, so the analyst answers with an empty structure and the dialog shows a result
 * nobody can act on; the refusal under the API's own bound is a 422 whose text no screen explains
 * either. So this number stays above those three, and the ai-service gate that owns the floor reads
 * the server's bounds out of `features.py` rather than restating them.
 */

import type { TextIssue } from "@/lib/i18n/issue";

/** The least pasted posting text either dialog will send. */
export const JD_TEXT_MIN_CHARS = 40;

/** Why a paste cannot be analysed yet, or `undefined` once it clears the floor. */
export function jdTextIssue(value: string): TextIssue | undefined {
  if (value.trim().length < JD_TEXT_MIN_CHARS) {
    return { key: "jd.pasteAtLeast", params: { min: JD_TEXT_MIN_CHARS } };
  }
  return undefined;
}
