/**
 * Chapter zero — the first week, playable (Epic 233).
 *
 * The playbook teaches the loop in prose. This is the loop rehearsed with a
 * finger before it ever sees a keyboard: seven scenes, three forks each, and a
 * verdict at the end that tells the reader which reader they will be. The
 * story is second person, and every choice is a real one the app walks the
 * reader through on the way to the closing page. No model calls — the value
 * is in the reader's honesty, not the machine's opinion. Choices live in
 * this browser only (`careeros.firstweek.v1`); completing it registers
 * nothing anywhere.
 */

export interface FirstWeekChoice {
  id: string;
  /** 0 · the foot-dragger · 1 · the honest middle · 2 · the shipper. */
  points: number;
}

export interface FirstWeekScene {
  id: string;
  choices: readonly FirstWeekChoice[];
}

export const FIRST_WEEK_SCENES: readonly FirstWeekScene[] = [
  {
    id: "upload",
    choices: [
      { id: "all", points: 2 },
      { id: "recent", points: 1 },
      { id: "polish", points: 0 },
    ],
  },
  {
    id: "jd",
    choices: [
      { id: "asis", points: 2 },
      { id: "note", points: 1 },
      { id: "blank", points: 0 },
    ],
  },
  {
    id: "match",
    choices: [
      { id: "evidence", points: 2 },
      { id: "flags", points: 1 },
      { id: "close", points: 0 },
    ],
  },
  {
    id: "gap",
    choices: [
      { id: "plan", points: 2 },
      { id: "incident", points: 1 },
      { id: "keep", points: 0 },
    ],
  },
  {
    id: "letter",
    choices: [
      { id: "slash", points: 2 },
      { id: "own", points: 2 },
      { id: "keep", points: 0 },
    ],
  },
  {
    id: "interview",
    choices: [
      { id: "evidence", points: 2 },
      { id: "wing", points: 1 },
      { id: "off", points: 0 },
    ],
  },
  {
    id: "call",
    choices: [
      { id: "calendar", points: 2 },
      { id: "tonight", points: 1 },
      { id: "crazy", points: 0 },
    ],
  },
];

const STORAGE_KEY = "careeros.firstweek.v1";

export const MAX_FIRST_WEEK_SCORE = FIRST_WEEK_SCENES.length * 2;
export const FIRST_WEEK_SCENE_COUNT = FIRST_WEEK_SCENES.length;

export type FirstWeekState = { choices: Record<string, string>; sentence: string };

export const EMPTY_FIRST_WEEK: FirstWeekState = { choices: {}, sentence: "" };

const POINTS = new Map<string, number>(
  FIRST_WEEK_SCENES.flatMap((scene) =>
    scene.choices.map((choice) => [`${scene.id}:${choice.id}`, choice.points] as const)
  )
);

export function firstWeekPoints(sceneId: string, choiceId: string): number {
  return POINTS.get(`${sceneId}:${choiceId}`) ?? 0;
}

export function firstWeekTotal(state: FirstWeekState): number {
  return Object.entries(state.choices).reduce(
    (sum, [sceneId, choiceId]) => sum + firstWeekPoints(sceneId, choiceId),
    0
  );
}

export function firstWeekAnswered(state: FirstWeekState): boolean {
  return FIRST_WEEK_SCENES.every((scene) => scene.id in state.choices);
}

/** The three readers the week produces. Keys are the bands the numbers keep. */
export function firstWeekVerdict(total: number): "architect" | "steady" | "reluctant" {
  if (total >= 9) return "architect";
  if (total >= 5) return "steady";
  return "reluctant";
}

function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

/** The stored state lives in this browser; nothing here is sent anywhere. */
export function loadFirstWeek(replica: Storage | null = storage()): FirstWeekState {
  if (!replica) return { ...EMPTY_FIRST_WEEK, choices: {} };
  try {
    const raw = replica.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY_FIRST_WEEK, choices: {} };
    const parsed = JSON.parse(raw) as Partial<FirstWeekState> | null;
    const choices =
      parsed?.choices && typeof parsed.choices === "object" && !Array.isArray(parsed.choices)
        ? Object.fromEntries(
            Object.entries(parsed.choices).filter(
              ([sceneId, choiceId]) =>
                typeof choiceId === "string" &&
                FIRST_WEEK_SCENES.some(
                  (scene) => scene.id === sceneId && scene.choices.some((c) => c.id === choiceId)
                )
            )
          )
        : {};
    return {
      choices,
      sentence: typeof parsed?.sentence === "string" ? parsed.sentence.slice(0, 1000) : "",
    };
  } catch {
    return { ...EMPTY_FIRST_WEEK, choices: {} };
  }
}

export function saveFirstWeek(state: FirstWeekState, replica: Storage | null = storage()): void {
  if (!replica) return;
  try {
    replica.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // best effort — the visible state is the honest artifact; the week belongs
    // to the reader, not the browser
  }
}

export function clearFirstWeek(replica: Storage | null = storage()): void {
  if (!replica) return;
  try {
    replica.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
