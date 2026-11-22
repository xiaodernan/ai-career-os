/**
 * Epic 385 — the echo. Everything on the interview page is a model's reading of an
 * answer; this module is the reader's own reading, done with arithmetic: how long
 * the answers are, how long their sentences run, which filler words repeat, whether
 * any figure ever appears, and whether the voice is "I" or "we".
 *
 * It is deliberately a pure function over the answer strings already on the page.
 * No endpoint, no provider, no new state — the same answers produce the same numbers
 * in either language, and a session that has not answered anything produces nothing.
 */

export interface EchoFiller {
  term: string;
  count: number;
}

export interface EchoNudge {
  /** An i18n key; the sentence itself belongs to the reader's language. */
  key: string;
  vars?: Record<string, string | number>;
  /** `watch` is a thing worth fixing; `info` is a thing worth knowing. */
  watch: boolean;
}

export interface AnswerEcho {
  answers: number;
  units: number;
  avgUnits: number;
  longest: number;
  sentences: number;
  avgSentence: number;
  fillers: EchoFiller[];
  fillerTotal: number;
  hedges: number;
  numbers: number;
  singular: number;
  plural: number;
  /** Singular share of first-person pronouns, 0..1; null when nobody said "I" or "we". */
  ownership: number | null;
  nudges: EchoNudge[];
}

const CJK = /[\u3400-\u9fff\uf900-\ufaff]/g;

/**
 * Fillers are literal sounds, not concepts, so they are not translated: a Chinese
 * "嗯" and an English "um" are the same event and both are shown as what was typed.
 * "Like" and "然后" are left out on purpose — both are ordinary words, and counting
 * them would punish correct prose.
 */
const FILLERS = ["um", "uh", "you know", "i mean", "kind of", "sort of", "basically", "嗯", "呃", "那个", "就是说"];

/** Hedges are different from fillers: they soften a claim the reader could own. */
const HEDGES = ["maybe", "perhaps", "probably", "i think", "i guess", "可能", "也许", "大概", "差不多"];

function escape(term: string): string {
  return term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isAscii(term: string): boolean {
  return /^[\x20-\x7e]+$/.test(term);
}

function countTerm(text: string, term: string): number {
  const pattern = isAscii(term) ? `\\b${escape(term)}\\b` : escape(term);
  const found = text.match(new RegExp(pattern, "gi"));
  return found?.length ?? 0;
}

/** A word in English, a character in Chinese; one number that means "how much was said". */
export function unitsOf(text: string): number {
  const cjk = (text.match(CJK) ?? []).length;
  const words = text.replace(CJK, " ").match(/[A-Za-z0-9][A-Za-z0-9'’.-]*/g)?.length ?? 0;
  return cjk + words;
}

function sentencesOf(text: string): number {
  return text
    .split(/[.!?。！？]+|\n+/)
    .filter((sentence) => unitsOf(sentence) > 0).length;
}

function firstPerson(text: string): { singular: number; plural: number } {
  const pluralEn = countTerm(text, "we") + countTerm(text, "us") + countTerm(text, "our") + countTerm(text, "ours");
  const women = countTerm(text, "我们");
  const pluralZh = women + countTerm(text, "咱们");
  const singularEn = countTerm(text, "i") + countTerm(text, "me") + countTerm(text, "my") + countTerm(text, "mine");
  // "我们" contains "我"; the plural has already been counted, so subtract it here.
  const singularZh = Math.max(0, countTerm(text, "我") - women);
  return { singular: singularEn + singularZh, plural: pluralEn + pluralZh };
}

const EMPTY: AnswerEcho = {
  answers: 0,
  units: 0,
  avgUnits: 0,
  longest: 0,
  sentences: 0,
  avgSentence: 0,
  fillers: [],
  fillerTotal: 0,
  hedges: 0,
  numbers: 0,
  singular: 0,
  plural: 0,
  ownership: null,
  nudges: [],
};

export function analyzeAnswers(answers: string[]): AnswerEcho {
  const kept = answers.map((answer) => answer.trim()).filter(Boolean);
  if (kept.length === 0) return { ...EMPTY };

  let units = 0;
  let sentences = 0;
  let longest = 0;
  let numbers = 0;
  let hedges = 0;
  let singular = 0;
  let plural = 0;
  const fillerCounts = new Map<string, number>();

  for (const answer of kept) {
    const size = unitsOf(answer);
    units += size;
    sentences += sentencesOf(answer);
    longest = Math.max(longest, size);
    numbers += answer.match(/\d+(?:[.,]\d+)?%?/g)?.length ?? 0;
    hedges += HEDGES.reduce((sum, term) => sum + countTerm(answer, term), 0);
    const voice = firstPerson(answer);
    singular += voice.singular;
    plural += voice.plural;
    for (const term of FILLERS) {
      const count = countTerm(answer, term);
      if (count > 0) fillerCounts.set(term, (fillerCounts.get(term) ?? 0) + count);
    }
  }

  const fillers = [...fillerCounts.entries()]
    .map(([term, count]) => ({ term, count }))
    .sort((a, b) => b.count - a.count || a.term.localeCompare(b.term))
    .slice(0, 4);
  const fillerTotal = [...fillerCounts.values()].reduce((sum, count) => sum + count, 0);
  const avgUnits = Math.round(units / kept.length);
  const avgSentence = sentences > 0 ? Math.round(units / sentences) : 0;
  const firstPersonTotal = singular + plural;

  const nudges: EchoNudge[] = [];
  if (avgUnits < 40) {
    nudges.push({ key: "interviews.detail.echoNudgeShort", vars: { avg: avgUnits }, watch: true });
  }
  if (fillerTotal >= 2 && fillers[0]) {
    nudges.push({
      key: "interviews.detail.echoNudgeFiller",
      vars: { term: fillers[0].term, count: fillers[0].count },
      watch: fillers[0].count >= 3,
    });
  }
  if (kept.length >= 2 && numbers === 0) {
    nudges.push({ key: "interviews.detail.echoNudgeNoNumbers", watch: true });
  }
  if (plural >= 3 && plural > singular) {
    nudges.push({ key: "interviews.detail.echoNudgeWe", watch: true });
  }
  if (longest >= 220) {
    nudges.push({ key: "interviews.detail.echoNudgeLong", vars: { longest }, watch: false });
  }
  if (avgSentence >= 35) {
    nudges.push({ key: "interviews.detail.echoNudgeRambling", vars: { avg: avgSentence }, watch: false });
  }

  return {
    answers: kept.length,
    units,
    avgUnits,
    longest,
    sentences,
    avgSentence,
    fillers,
    fillerTotal,
    hedges,
    numbers,
    singular,
    plural,
    ownership: firstPersonTotal > 0 ? singular / firstPersonTotal : null,
    nudges: nudges.slice(0, 4),
  };
}
