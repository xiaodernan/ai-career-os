import { describe, expect, it } from "vitest";
import {
  REVIEW_CARD_HEIGHT,
  REVIEW_CARD_WIDTH,
  drawReviewCard,
  type CanvasLike,
} from "./review-card";

function stubCtx() {
  const texts: Array<{ text: string | CanvasGradient | CanvasPattern; x: number; y: number }> = [];
  const rects: Array<{ x: number; y: number; w: number; h: number }> = [];
  const arcs: number[] = [];
  const strokes: number[] = [];
  const ctx: CanvasLike = {
    fillStyle: "#000",
    strokeStyle: "#000",
    lineWidth: 1,
    globalAlpha: 1,
    font: "",
    textAlign: "left",
    beginPath() {},
    arc(x, y, radius) {
      arcs.push(x, y, radius);
    },
    moveTo() {},
    lineTo() {},
    closePath() {},
    fill() {},
    stroke() {},
    fillRect(x, y, w, h) {
      rects.push({ x, y, w, h });
    },
    fillText(text) {
      texts.push({ text, x: 0, y: 0 });
    },
    measureText: () => ({ width: 42 }),
  };
  return { ctx, texts, rects, arcs, strokes };
}

const NUMBERS = {
  applications: 37,
  interviews: 9,
  offers: 2,
  letters: 5,
  notes: 11,
  daysShowed: 14,
  grandTotal: 88,
  year: "2026",
};

const STRINGS = {
  eyebrow: "AI CAREER OS",
  headline: "The search in review",
  applications: "Applications filed",
  interviews: "Interviews held",
  offers: "Offers on the shelf",
  letters: "Letters kept",
  daysShowed: "Days you showed up",
  stripRight: "total actions taken",
  signOff: "Written from records, not from memory.",
  dateLine: "Nov 15, 2026",
};

describe("drawReviewCard", () => {
  it("paints the full card with every number the caller lent it", () => {
    const { ctx, texts, rects } = stubCtx();
    drawReviewCard(ctx, NUMBERS, STRINGS);

    const drawn = texts.map((t) => String(t.text));
    expect(drawn).toContain("AI CAREER OS");
    expect(drawn).toContain("The search in review");
    expect(drawn).toContain("37");
    expect(drawn).toContain("9");
    expect(drawn).toContain("2");
    expect(drawn).toContain("5");
    expect(drawn).toContain("14");
    expect(drawn).toContain("88");
    expect(drawn).toContain("Applications filed".toUpperCase());
    expect(drawn).toContain("Written from records, not from memory.");

    // Background + frame + 4 tiles + 1 strip.
    expect(rects.length).toBeGreaterThanOrEqual(6);
    // 3 arcs: the two vignette ellipses and none other.
    expect(texts.length).toBeGreaterThanOrEqual(15);
  });

  it("uses the reader's strings, not raw keys, in both languages", () => {
    const { ctx, texts } = stubCtx();
    drawReviewCard(ctx, NUMBERS, {
      ...STRINGS,
      headline: "这一年，一路走来",
      applications: "投出的申请",
      signOff: "一切都有据可查。",
    });
    const drawn = texts.map((t) => String(t.text));
    expect(drawn).toContain("这一年，一路走来");
    expect(drawn).toContain("投出的申请".toUpperCase());
    expect(drawn).toContain("一切都有据可查。");
  });

  it("keeps a stable, offline geometry", () => {
    expect(REVIEW_CARD_WIDTH).toBe(1080);
    expect(REVIEW_CARD_HEIGHT).toBe(1350);
  });
});
