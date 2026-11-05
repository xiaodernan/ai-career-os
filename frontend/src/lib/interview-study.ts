/**
 * 60.1: one study item, written as the note the knowledge base will keep.
 *
 * The report's study list is advice the reader loses the moment the tab closes:
 * the next session is generated fresh, and the copilot cannot quote a sentence
 * that only ever existed in a component. A note is different -- `createNote`
 * ingests its text, so what the rehearsal said to work on becomes something the
 * next answer can cite. This is the fold from one shape to the other, kept pure
 * so the wording is testable without a browser or a server.
 */

export interface StudySource {
  title?: string;
  why?: string;
  url?: string;
}

export interface NoteDraft {
  title: string;
  content: string;
  tags: string[];
}

/** The two tags every kept study item carries, so the knowledge page can find them. */
export const STUDY_NOTE_TAGS = ["interview", "study"];

/** 61.3: a kept rewrite is the report's other kind of advice, and its own tag says so. */
export const BETTER_ANSWER_TAGS = ["interview", "answer"];

/** `NoteRequest` caps the title at 200 characters; the draft never asks for more. */
const MAX_TITLE = 200;

/**
 * The note for one study item. The title is the topic (or the caller's fallback
 * for an untitled item); the body is the reason, the resource and -- 60.2 -- the
 * origin the caller phrased ("from your rehearsal for ..."), each on its own
 * paragraph. An item with nothing else still keeps its topic as the body rather
 * than sending the blank content `NoteRequest` refuses.
 */
export function studyNoteDraft(
  item: StudySource,
  fallbackTitle: string,
  origin?: string
): NoteDraft {
  const title = (item.title ?? "").trim().slice(0, MAX_TITLE) || fallbackTitle.slice(0, MAX_TITLE);
  const body = [item.why?.trim(), item.url?.trim(), origin?.trim()].filter(
    (part): part is string => Boolean(part)
  );
  return {
    title,
    content: body.length > 0 ? body.join("\n\n") : title,
    tags: [...STUDY_NOTE_TAGS],
  };
}

/**
 * 61.3: one stronger answer, written as a note. The question becomes the title
 * (so the note list reads like a list of answers to things), the rewrite becomes
 * the body, and the origin line from 60.2 rides along. An answer with no question
 * is still worth keeping -- the caller's fallback titles it.
 */
export function betterAnswerNoteDraft(
  item: { question?: string; answer: string },
  fallbackTitle: string,
  origin?: string
): NoteDraft {
  const title = (item.question ?? "").trim().slice(0, MAX_TITLE) || fallbackTitle.slice(0, MAX_TITLE);
  const body = [item.answer.trim(), origin?.trim()].filter(
    (part): part is string => Boolean(part)
  );
  return {
    title,
    content: body.join("\n\n"),
    tags: [...BETTER_ANSWER_TAGS],
  };
}

/** 63.1: a gap the grader named is advice too, and its own tag says so. */
export const GAP_NOTE_TAGS = ["interview", "gap"];

/**
 * 63.1: one missing concept, written as a note.
 *
 * A gap is usually one short line -- "could not explain why a B-tree keeps
 * leaves linked" -- so the line itself is the title and, when the item says
 * nothing else, the body too: an empty body is what `NoteRequest` refuses, and a
 * gap with no explanation is still a thing to study. The 60.2 origin line rides
 * along so the note remembers which rehearsal found it.
 */
export function gapNoteDraft(gap: string, fallbackTitle: string, origin?: string): NoteDraft {
  const text = gap.trim();
  const title = text.slice(0, MAX_TITLE) || fallbackTitle.slice(0, MAX_TITLE);
  const body = [text, origin?.trim()].filter((part): part is string => Boolean(part));
  return {
    title,
    content: body.length > 0 ? body.join("\n\n") : title,
    tags: [...GAP_NOTE_TAGS],
  };
}
