import { describe, expect, it } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { Avatar, AvatarFallback, AvatarImage } from "./avatar";

/**
 * 360: the reader's picture, whole.
 *
 * The brief names it directly -- "我的头像被压缩变小、边缘被裁掉" -- and the cause
 * was one Tailwind class: `object-cover` fills the circle by cropping whatever
 * does not fit, so a wide picture lost its top and bottom and the reader saw a
 * slice of their own face. The image now fits inside the frame
 * (`object-contain`) over a muted background that fills the letterbox.
 *
 * The trade is honest and stated in the component: a non-square picture no longer
 * fills the circle edge to edge. A crop is a picture the reader did not choose.
 */

const SRC = readFileSync(fileURLToPath(new URL("./avatar.tsx", import.meta.url)), "utf8");

/** The class list the image actually ships, read out of its own cn(...) call. */
function imageClasses(): string {
  const at = SRC.indexOf('data-slot="avatar-image"');
  const block = SRC.slice(at, at + 400);
  return block;
}

describe("the avatar image fits inside its frame", () => {
  it("scales to contain rather than cropping to cover", () => {
    // The class the image renders with, not the prose that explains why it changed:
    // the comment above it names the old class on purpose, so a bare source search
    // for "object-cover" would red on the explanation rather than the regression.
    const classes = imageClasses();
    expect(classes).toContain("object-contain");
    expect(classes).not.toMatch(/object-cover/);
  });

  it("centres the picture and fills the letterbox with the muted background", () => {
    // object-contain leaves room beside a non-square image; without a background
    // there, a transparent PNG would show the fallback's initials through the gap.
    const classes = imageClasses();
    expect(classes).toContain("object-center");
    expect(classes).toContain("bg-muted");
  });

  it("keeps the circle and the clip on the root", () => {
    // Radix mounts Avatar.Image only once the picture has loaded, so a server
    // render draws the fallback -- the image's own classes are pinned from the
    // source above, and what a render can prove is the frame around them.
    const html = renderToStaticMarkup(
      <Avatar>
        <AvatarImage src="https://example.com/a.png" alt="a" />
        <AvatarFallback>ZX</AvatarFallback>
      </Avatar>
    );
    expect(html).toContain("rounded-full");
    // The root still clips: a picture that overflows a circle would be a worse
    // bug than the one this fixed.
    expect(html).toContain("overflow-hidden");
    expect(html).toContain("size-8");
  });
});
