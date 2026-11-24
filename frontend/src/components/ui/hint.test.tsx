import { describe, expect, it } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Hint } from "./hint";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectTrigger } from "@/components/ui/select";

/**
 * 420: a hint may not overwrite the state attribute of what it wraps.
 *
 * The jobs board's tabs, sort select and dialog buttons all gained teaching tips,
 * and the composition is the risky half: Radix `Slot` hands the caller's props
 * precedence, and `TooltipTrigger` writes `data-state` -- which is also the
 * attribute `tabs.tsx` reads to paint the selected tab and its underline. Wrapped
 * directly, the active tab reported `aria-selected="true"` beside
 * `data-state="closed"`, which is the tooltip's state, not the tab's.
 *
 * `anchor="span"` exists for exactly that class of control, and these are the two
 * shapes measured side by side: the default binding still puts the tip on the
 * button itself (the case every other screen relies on), and the span binding
 * leaves the control's own attributes untouched.
 */

const TAB = (anchor?: "child" | "span") =>
  renderToStaticMarkup(
    <Tabs value="discover">
      <TabsList variant="line">
        <Hint label="Everything that answers the panel" anchor={anchor}>
          <TabsTrigger value="discover">Discover</TabsTrigger>
        </Hint>
        <TabsTrigger value="saved">Saved</TabsTrigger>
      </TabsList>
    </Tabs>
  );

/** The markup of the tab button whose label is `text`, with its attributes. */
function tabMarkup(markup: string, text: string): string {
  const start = markup.indexOf(`>${text}</`);
  const open = markup.lastIndexOf("<button", start);
  return markup.slice(open, start + text.length + 4);
}

describe("the default binding, which every other screen relies on", () => {
  it("attaches the tip to the control itself", () => {
    const markup = TAB();
    expect(tabMarkup(markup, "Discover")).toContain('data-slot="tooltip-trigger"');
    expect(markup).not.toContain('class="contents"');
  });

  it("is why a stateful control cannot be wrapped directly", () => {
    // The tooltip's own state lands on the button: the clobber `anchor="span"`
    // prevents, pinned here so the reason the prop exists stays in the file.
    expect(tabMarkup(TAB(), "Discover")).toContain('aria-selected="true"');
    expect(tabMarkup(TAB(), "Discover")).toContain('data-state="closed"');
    // The unwrapped sibling keeps the tab's own value, which is the shape the
    // active-tab styles were written against.
    expect(tabMarkup(TAB(), "Saved")).toContain('data-state="inactive"');
  });
});

describe("the span binding, for controls that own data-state", () => {
  it("leaves the selected tab its own state", () => {
    const markup = TAB("span");
    expect(tabMarkup(markup, "Discover")).toContain('data-state="active"');
    expect(tabMarkup(markup, "Discover")).toContain('aria-selected="true"');
  });

  it("still puts the tab behind a tooltip trigger", () => {
    const markup = TAB("span");
    const wrapper = markup.slice(
      markup.indexOf('<span class="contents"'),
      markup.indexOf(">Discover</")
    );
    expect(wrapper).toContain('data-slot="tooltip-trigger"');
  });

  it("costs no layout box", () => {
    // `display: contents` is what keeps the flex TabsList sizing the same.
    expect(TAB("span")).toContain('class="contents"');
  });
});

describe("a select owns its state too", () => {
  const picker = (anchor?: "child" | "span") =>
    renderToStaticMarkup(
      <Select defaultOpen>
        <Hint label="Move this card to another stage" anchor={anchor}>
          <SelectTrigger>Saved</SelectTrigger>
        </Hint>
      </Select>,
    );

  it("shows why the board's stage picker uses the span binding", () => {
    const direct = picker();
    expect(direct).toContain('role="combobox"');
    expect(direct).toContain('data-slot="tooltip-trigger"');
    expect(direct).toContain('data-state="closed"');
    expect(direct).not.toContain('data-state="open"');
  });

  it("keeps the select trigger free of the tooltip's state attribute", () => {
    const isolated = picker("span");
    const start = isolated.lastIndexOf("<button", isolated.indexOf('data-slot="select-trigger"'));
    const trigger = isolated.slice(start, isolated.indexOf("</button>", start));
    expect(trigger).toContain('data-state="open"');
    expect(trigger).not.toContain('data-slot="tooltip-trigger"');
    expect(trigger).not.toContain('data-state="closed"');
    expect(isolated).toContain('<span class="contents" data-state="closed" data-slot="tooltip-trigger"');
  });
});
