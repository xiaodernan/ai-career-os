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

export interface StudyNoteDraft {
  title: string;
  content: string;
  tags: string[];
}

/** The two tags every kept study item carries, so the knowledge page can find them. */
export const STUDY_NOTE_TAGS = ["interview", "study"];

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
): StudyNoteDraft {
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
