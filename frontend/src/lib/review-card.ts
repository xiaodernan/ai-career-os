/**
 * The year in review (Epic 224) — one image, honestly made.
 *
 * The letters say the search; the card shows it. Every number below is the
 * product's own route answer (the same totals the ceremony renders), and the
 * image carries nothing but those numbers and the product's own words. This
 * module is the layout: a deterministic function from *the data in hand* to
 * canvas drawing calls — no images, no fonts beyond what the machine has,
 * testable with a stub context.
 */

/** The numbers this card is allowed to say — always the caller's own routes. */
export interface ReviewCardNumbers {
  applications: number;
  interviews: number;
  offers: number;
  letters: number;
  notes: number;
  daysShowed: number;
  grandTotal: number;
  year: string;
}

export interface ReviewCardStrings {
  eyebrow: string;
  headline: string;
  applications: string;
  interviews: string;
  offers: string;
  letters: string;
  daysShowed: string;
  stripRight: string;
  signOff: string;
  /** e.g. "today's date in the reader's language" — the caller formats it. */
  dateLine: string;
}

export const REVIEW_CARD_WIDTH = 1080;
export const REVIEW_CARD_HEIGHT = 1350;

/** A canvas-2d-shaped slice of the API — exactly what this module calls. */
export interface CanvasLike {
  fillStyle: string | CanvasGradient | CanvasPattern;
  strokeStyle: string | CanvasGradient | CanvasPattern;
  lineWidth: number;
  globalAlpha: number;
  beginPath(): void;
  arc(x: number, y: number, radius: number, startAngle: number, endAngle: number): void;
  moveTo(x: number, y: number): void;
  lineTo(x: number, y: number): void;
  closePath(): void;
  fill(): void;
  stroke(): void;
  fillRect(x: number, y: number, w: number, h: number): void;
  fillText(text: string, x: number, y: number): void;
  measureText(text: string): { width: number };
  font: string;
  textAlign: CanvasTextAlign;
}

const INK = "#efeaf6";
const MUTED = "#8b86a3";
const ACCENT = "#a78bfa";
const CARD = "#12101d";
const PANEL = "#1b1830";
const STROKE = "#2a2740";

/** Paint the card. The caller owns the numbers and the strings; this owns the look. */
export function drawReviewCard(ctx: CanvasLike, numbers: ReviewCardNumbers, strings: ReviewCardStrings): void {
  const W = REVIEW_CARD_WIDTH;
  const H = REVIEW_CARD_HEIGHT;

  // Background: near-black editorial with two offset brass arcs.
  ctx.fillStyle = CARD;
  ctx.fillRect(0, 0, W, H);

  // Vignette arcs.
  ctx.strokeStyle = STROKE;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(-160, -160, 760, 0, Math.PI * 2);
  ctx.closePath();
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(W + 160, H + 160, 820, 0, Math.PI * 2);
  ctx.closePath();
  ctx.stroke();

  // Eyebrow row: product mark + date.
  ctx.font = "600 22px Georgia, serif";
  ctx.fillStyle = ACCENT;
  ctx.textAlign = "left";
  ctx.fillText(strings.eyebrow, 96, 136);
  ctx.font = "500 20px Georgia, serif";
  ctx.fillStyle = MUTED;
  ctx.textAlign = "right";
  ctx.fillText(strings.dateLine, W - 96, 136);

  // The headline — the reader's year, in the reader's own words.
  ctx.textAlign = "left";
  ctx.font = "italic 500 92px Georgia, serif";
  ctx.fillStyle = INK;
  ctx.fillText(strings.headline, 96, 280);

  // Divider.
  ctx.strokeStyle = STROKE;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(96, 320);
  ctx.lineTo(W - 96, 320);
  ctx.closePath();
  ctx.stroke();

  // The grid of the record — 2×2 tiles bound to route totals.
  const tiles: Array<[string, string]> = [
    [String(numbers.applications), strings.applications],
    [String(numbers.interviews), strings.interviews],
    [String(numbers.offers), strings.offers],
    [String(numbers.letters), strings.letters],
  ];
  const tileW = (W - 96 * 2 - 48) / 2;
  const tileH = 210;
  const gridTop = 360;
  for (let i = 0; i < tiles.length; i += 1) {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 96 + col * (tileW + 48);
    const y = gridTop + row * (tileH + 32);
    ctx.fillStyle = PANEL;
    ctx.fillRect(x, y, tileW, tileH);
    ctx.strokeStyle = STROKE;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + tileW, y);
    ctx.closePath();
    ctx.stroke();

    ctx.fillStyle = INK;
    ctx.font = "600 96px Georgia, serif";
    ctx.textAlign = "left";
    ctx.fillText(tiles[i][0], x + 36, y + 108);
    ctx.font = "500 22px Georgia, serif";
    ctx.fillStyle = MUTED;
    ctx.fillText(tiles[i][1].toUpperCase(), x + 36, y + 158);
  }

  // The streak strip — days showed and the grand total.
  const stripTop = gridTop + 2 * (tileH + 32) + 24;
  ctx.fillStyle = PANEL;
  ctx.fillRect(96, stripTop, W - 192, 170);
  ctx.strokeStyle = ACCENT;
  ctx.globalAlpha = 0.35;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(96, stripTop);
  ctx.lineTo(W - 96, stripTop);
  ctx.closePath();
  ctx.stroke();
  ctx.globalAlpha = 1;

  ctx.font = "500 26px Georgia, serif";
  ctx.fillStyle = MUTED;
  ctx.textAlign = "left";
  ctx.fillText(strings.daysShowed.toUpperCase(), 132, stripTop + 62);
  ctx.font = "600 84px Georgia, serif";
  ctx.fillStyle = INK;
  ctx.fillText(String(numbers.daysShowed), 132, stripTop + 140);

  const rightX = W - 132;
  ctx.textAlign = "right";
  ctx.font = "600 84px Georgia, serif";
  ctx.fillStyle = INK;
  ctx.fillText(String(numbers.grandTotal), rightX, stripTop + 140);
  ctx.font = "500 24px Georgia, serif";
  ctx.fillStyle = MUTED;
  ctx.fillText(strings.stripRight.toUpperCase(), rightX, stripTop + 58);

  // Sign-off: the line the product itself writes.
  ctx.textAlign = "left";
  ctx.font = "italic 500 26px Georgia, serif";
  ctx.fillStyle = MUTED;
  ctx.fillText(strings.signOff, 96, H - 96);
}
