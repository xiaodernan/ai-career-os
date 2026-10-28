/**
 * A field's complaint, as the sentence's identity rather than the sentence.
 *
 * The checks that guard user input -- an email, a password, a pasted
 * posting -- answer with a key in the locale table and the values its
 * holes take. The screen turns the key into words at paint time, in the
 * reader's language. A check that returned English instead put English
 * under a Chinese label, which is the bug this shape exists to make
 * impossible.
 */

export interface TextIssue {
  key: string;
  params?: Record<string, string | number>;
}

export type Translate = (key: string, vars?: Record<string, string | number>) => string;

/** The sentence for an issue, in the reader's language, or undefined when there is none. */
export function issueText(issue: TextIssue | undefined, t: Translate): string | undefined {
  return issue === undefined ? undefined : t(issue.key, issue.params);
}
