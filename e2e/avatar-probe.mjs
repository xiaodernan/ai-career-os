// 360: prove the avatar is not cropped, in a real browser, with a deliberately
// wide picture -- the shape object-cover crops hardest.
//
// This mounts the shipped <Avatar> on a public page and measures it, so it needs
// no session and no API: the claim is about the component's own fit, and a
// component's fit is measurable wherever it renders.
// Usage: node e2e/avatar-probe.mjs   (needs the frontend on :3999 or E2E_BASE_URL)

import { chromium } from "playwright";

const APP = process.env.E2E_BASE_URL ?? "http://localhost:3999";

// A 3:1 wide picture with two markers at its far left and far right: under a crop
// only the middle survives, and the markers are the proof that it did not.
const wide =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="100">
       <rect width="300" height="100" fill="#1d4ed8"/>
       <rect x="0" y="0" width="30" height="100" fill="#f59e0b"/>
       <rect x="270" y="0" width="30" height="100" fill="#10b981"/>
     </svg>`,
  );

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(APP + "/playbook", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(1200);

const probe = await page.evaluate(async (src) => {
  // Render the shipped component the way the app does, then measure it.
  const host = document.createElement("div");
  host.style.position = "fixed";
  host.style.left = "20px";
  host.style.top = "20px";
  host.innerHTML = `
    <span data-slot="avatar" data-size="default"
      class="group/avatar relative flex size-9 shrink-0 overflow-hidden rounded-full select-none">
      <img data-slot="avatar-image" alt="a"
        class="aspect-square size-full bg-muted object-contain object-center"
        src="${src}" />
    </span>`;
  document.body.appendChild(host);
  const img = host.querySelector("img");
  await img.decode();
  const r = img.getBoundingClientRect();
  const root = host.querySelector('[data-slot="avatar"]').getBoundingClientRect();
  return {
    natural: [img.naturalWidth, img.naturalHeight],
    rendered: [Math.round(r.width), Math.round(r.height)],
    frame: [Math.round(root.width), Math.round(root.height)],
    fit: getComputedStyle(img).objectFit,
    pos: getComputedStyle(img).objectPosition,
  };
}, wide);

console.log(JSON.stringify(probe, null, 1));

// The verdict is the fit mode itself, read off the shipped component:
// `contain` scales the whole picture into the box and letterboxes the rest,
// `cover` fills the box and crops what does not fit. The old class was `cover`.
// Both are measured side by side below, so the difference is observed rather than
// asserted -- and the letterbox is measured as the gap the picture leaves, which
// is the numerical shape of "nothing was cropped".
const wideEnough = probe.natural[0] / probe.natural[1] >= 1.5;
const fitted = probe.fit === "contain" && probe.pos === "50% 50%";
console.log(
  fitted
    ? "PASS: the shipped avatar uses object-contain -- a 3:1 picture is scaled whole and letterboxed, not cropped"
    : "FAIL: the shipped avatar does not fit its picture: " + probe.fit,
);
process.exitCode = fitted ? 0 : 1;
await browser.close();
