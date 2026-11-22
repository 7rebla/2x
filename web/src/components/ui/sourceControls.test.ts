// Every button, text field and choice of the app comes from the building
// blocks in this folder (work order 077). Without this check a new page would
// copy button classes again and bring back the mixed heights.
import { describe, expect, it } from "vitest";

const sources = import.meta.glob<string>(["/src/**/*.tsx", "!/src/**/*.test.tsx", "!/src/components/ui/**"], {
  query: "?raw",
  import: "default",
  eager: true,
});

/** Native inputs that keep their own look: check boxes and radio buttons. File choosers use FileInput (work order 088). */
const NATIVE_INPUT_TYPES = new Set(["checkbox", "radio"]);

/** The source without comments (a comment may name an element); line numbers stay the same. */
function withoutComments(text: string): string {
  return text
    .replace(/\/\*[\s\S]*?\*\//g, (comment) => comment.replace(/[^\n]/g, " "))
    .replace(/^[ \t]*\/\/.*$/gm, "");
}

function findAll(pattern: RegExp, keep: (match: RegExpExecArray) => boolean = () => true): string[] {
  const found: string[] = [];
  for (const [path, source] of Object.entries(sources)) {
    const text = withoutComments(source);
    for (const match of text.matchAll(pattern)) {
      if (keep(match)) {
        const line = text.slice(0, match.index).split("\n").length;
        found.push(`${path}:${String(line)}: ${match[0].slice(0, 60)}`);
      }
    }
  }
  return found;
}

describe("controls in the source code", () => {
  it("reads the pages and components, but not the building blocks", () => {
    expect(Object.keys(sources)).toContain("/src/pages/AuditPage.tsx");
    expect(Object.keys(sources)).toContain("/src/components/UserMenu.tsx");
    expect(Object.keys(sources)).toContain("/src/LanguageSwitch.tsx");
    expect(Object.keys(sources).some((path) => path.includes("/components/ui/"))).toBe(false);
    expect(Object.keys(sources).some((path) => path.includes(".test."))).toBe(false);
  });

  it("ignores elements named in comments", () => {
    expect(withoutComments("a\n/* a <select>\n */\n// <button>\nb")).toBe("a\n             \n   \n\nb");
  });

  it("has no native button, select or textarea outside components/ui", () => {
    expect(findAll(/<(?:button|select|textarea)\b/g)).toEqual([]);
  });

  it("has native inputs only for check boxes and radio buttons", () => {
    // Inputs close with "/>"; an arrow function in an attribute only has "=>".
    const others = findAll(/<input\b[\s\S]*?\/>/g, (match) => {
      const type = /\btype="([a-z]+)"/.exec(match[0])?.[1];
      return type === undefined || !NATIVE_INPUT_TYPES.has(type);
    });
    expect(others).toEqual([]);
  });

  it("chooses files only through FileInput", () => {
    // Catches a file input written outside the building block in any form.
    expect(findAll(/\btype=["{]?["'`]?file\b/g)).toEqual([]);
    expect(Object.values(sources).some((source) => source.includes("<FileInput"))).toBe(true);
  });

  it("has no copy of the button classes", () => {
    // A filled accent background with padding, as the old buttons had (bg-accent … px-…).
    // bg-accent-soft (highlighted search text, the current navigation entry) is not a button colour.
    expect(findAll(/\bbg-accent(?![\w-])[^"`\n]*\bpx-\d/g)).toEqual([]);
    expect(findAll(/\bdisabled:opacity-\d+/g)).toEqual([]);
  });
});
