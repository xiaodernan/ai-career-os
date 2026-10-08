/**
 * WCAG 2.4.1 (Bypass Blocks).
 *
 * The app shell puts a nine-item sidebar and a topbar with five controls ahead of `<main>`,
 * so a keyboard traveller repeats every one of them on every page before reaching the content
 * they came for. This link is the bypass: the shell's first focusable element, and a jump
 * straight to the landmark the page is about.
 *
 * It rests a full link-height above the viewport and slides in on focus, rather than using
 * `sr-only`/`focus:not-sr-only`. That pair is Tailwind's documented skip-link recipe, but it
 * needs `focus:fixed` to place the revealed link and `not-sr-only` resets `position` to
 * `static`, so the two fight over one property and the winner is decided by the engine's
 * utility ordering rather than by this file. Translating a `fixed` element has no such
 * collision, and `transition-transform` is short enough that the reduced-motion override in
 * globals.css turns the slide into a snap.
 *
 * `tabIndex={-1}` on the target is the other half and lives in the shell: a fragment jump
 * moves the viewport but not the focus, so without it the next Tab would start again from the
 * top of the document and the link would have bought nothing.
 */
export function SkipLink() {
  return (
    <a
      href="#main"
      className="fixed left-4 top-4 z-50 -translate-y-16 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground shadow-pop transition-transform focus:translate-y-0"
    >
      Skip to content
    </a>
  );
}
