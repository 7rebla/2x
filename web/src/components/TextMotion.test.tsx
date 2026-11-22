import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeMatchMedia } from "../test/fakeMatchMedia.ts";
import { reducedMotionQuery } from "../theme/settings.ts";
import { refreshDisplay, updateDisplaySettings } from "../theme/store.ts";
import indexCss from "../index.css?raw";
import {
  AnimatedHeading,
  HEADING_STORAGE_KEY,
  headingShown,
  LoadingText,
  markHeadingShown,
  MaskedTitle,
  markTyped,
  TYPED_STORAGE_KEY,
  typedCharacters,
  TypedText,
  typedRuns,
} from "./TextMotion.tsx";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  window.sessionStorage.clear();
  refreshDisplay();
});

/** Class names of the element and everything inside it that belong to an animation. */
function animationClasses(element: Element): string[] {
  return [element, ...element.querySelectorAll("*")]
    .flatMap((node) => [...node.classList])
    .filter((name) => name.startsWith("tx-"));
}

describe("text animations", () => {
  it("splits a heading into words (pattern A) and keeps its text and name", () => {
    render(<AnimatedHeading text="Standorte, Bereiche und Geräte" />);
    const heading = screen.getByRole("heading", { level: 1, name: "Standorte, Bereiche und Geräte" });
    expect(heading.textContent).toBe("Standorte, Bereiche und Geräte");
    expect(heading.classList.contains("tx-clear")).toBe(true);
    const words = heading.querySelectorAll<HTMLElement>(".tx-word");
    expect([...words].map((word) => word.textContent)).toEqual(["Standorte,", "Bereiche", "und", "Geräte"]);
    expect([...words].map((word) => word.style.getPropertyValue("--tx-index"))).toEqual(["0", "1", "2", "3"]);
  });

  it("writes page headings and titles as h1 unless a level is given (work order 078)", () => {
    render(
      <>
        <AnimatedHeading text="Change log" />
        <MaskedTitle text="test-device" />
      </>,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Change log" }).tagName).toBe("H1");
    expect(screen.getByRole("heading", { level: 1, name: "test-device" }).tagName).toBe("H1");
  });

  it("masks a title line (pattern B)", () => {
    render(<MaskedTitle text="Steuerung PL3" level={3} testId="title" />);
    const title = screen.getByTestId("title");
    expect(title.tagName).toBe("H3");
    expect(title.textContent).toBe("Steuerung PL3");
    expect(animationClasses(title)).toEqual(["tx-mask", "tx-line"]);
  });

  it("lets a loading text shimmer without changing it (pattern D)", () => {
    const { container } = render(<LoadingText text="Wird geladen…" />);
    expect(container.textContent).toBe("Wird geladen…");
    expect(container.querySelector(".tx-sheen")?.textContent).toBe("Wird geladen");
    expect(container.querySelector(".tx-dots")?.textContent).toBe("…");
  });

  it("renders no animation class when the user reduces motion", () => {
    act(() => {
      updateDisplaySettings({ reduceMotion: true });
    });
    const { container } = render(
      <div>
        <AnimatedHeading text="Change log" />
        <MaskedTitle text="test-device" />
        <LoadingText text="Loading…" />
      </div>,
    );
    expect(animationClasses(container)).toEqual([]);
    expect(screen.getByRole("heading", { name: "Change log" }).textContent).toBe("Change log");
    expect(container.textContent).toBe("Change logtest-deviceLoading…");
  });

  it("renders no animation class when the operating system asks for reduced motion", () => {
    fakeMatchMedia({ [reducedMotionQuery]: true });
    act(() => {
      refreshDisplay();
    });
    const { container } = render(
      <div>
        <AnimatedHeading text="Map" />
        <LoadingText text="Checking…" />
      </div>,
    );
    expect(animationClasses(container)).toEqual([]);
    expect(document.documentElement.dataset.motion).toBe("reduce");
  });

  it("switches the animation off while the heading is shown", () => {
    render(<AnimatedHeading text="Self-test" />);
    expect(animationClasses(screen.getByRole("heading"))).toEqual(["tx-clear", "tx-word"]);
    act(() => {
      updateDisplaySettings({ reduceMotion: true });
    });
    expect(animationClasses(screen.getByRole("heading"))).toEqual([]);
  });
});

describe("heading fade (pattern A, E-65)", () => {
  it("fades in only the first heading of a browser session", () => {
    const first = render(<AnimatedHeading text="Geräte" />);
    expect(animationClasses(screen.getByRole("heading"))).toEqual(["tx-clear", "tx-word"]);
    expect(window.sessionStorage.getItem(HEADING_STORAGE_KEY)).toBe("1");
    expect(headingShown()).toBe(true);
    // Still fading on the same page, although the session is marked now.
    first.rerender(<AnimatedHeading text="Geräte" />);
    expect(animationClasses(screen.getByRole("heading"))).toEqual(["tx-clear", "tx-word"]);
    first.unmount();

    // Next page in the same session: the heading stands there at once.
    const { container } = render(<AnimatedHeading text="Änderungsprotokoll" />);
    expect(container.innerHTML).toBe('<h1 class="text-2xl font-semibold">Änderungsprotokoll</h1>');
  });

  it("shows a changed text at once instead of fading in again", () => {
    const { rerender } = render(<AnimatedHeading text="Einstellungen" />);
    rerender(<AnimatedHeading text="Settings" />);
    const heading = screen.getByRole("heading", { name: "Settings" });
    expect(animationClasses(heading)).toEqual([]);
    expect(heading.textContent).toBe("Settings");
  });

  it("counts the session as done when the user reduces motion", () => {
    act(() => {
      updateDisplaySettings({ reduceMotion: true });
    });
    render(<AnimatedHeading text="Map" />).unmount();
    expect(headingShown()).toBe(true);
    act(() => {
      updateDisplaySettings({ reduceMotion: false });
    });
    expect(animationClasses(render(<AnimatedHeading text="Map" />).container)).toEqual([]);
  });

  it("never fades in and never fails without a usable storage", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(headingShown()).toBe(true);
    expect(() => {
      markHeadingShown();
    }).not.toThrow();
    const { container } = render(<AnimatedHeading text="Map" />);
    expect(animationClasses(container)).toEqual([]);
    expect(screen.getByRole("heading", { name: "Map" })).toBeDefined();
  });

  it("fades without blur and is done within 400 ms", () => {
    const keyframes = /@keyframes tx-clear \{([\s\S]*?)\n\}/.exec(indexCss)?.[1] ?? "";
    expect(keyframes).toMatch(/opacity: 0;/);
    expect(keyframes).not.toMatch(/filter|blur/);
    const rule = cssRule(".tx-clear .tx-word");
    expect(rule).not.toMatch(/filter|blur/);
    const duration = Number(/animation: tx-clear (\d+)ms /.exec(rule)?.[1]);
    const delay = /animation-delay: calc\(min\(var\(--tx-index, 0\), (\d+)\) \* (\d+)ms\);/.exec(rule);
    const maxSteps = Number(delay?.[1]);
    const step = Number(delay?.[2]);
    expect(duration).toBeGreaterThan(0);
    expect(duration + maxSteps * step).toBeLessThanOrEqual(400);
  });
});

/** The rule for one selector in index.css (its declarations). */
function cssRule(selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\:]/g, "\\$&");
  const match = new RegExp(`(?:^|\\n)\\s*${escaped} \\{([^}]*)\\}`).exec(indexCss);
  if (match === null) {
    throw new Error(`no rule for ${selector} in index.css`);
  }
  return match[1] ?? "";
}

/** The typed characters of the layer, as drawn from data-char. */
function typedChars(container: Element): string[] {
  return [...container.querySelectorAll<HTMLElement>(".tx-type-char")].map((char) => char.dataset.char ?? "");
}

describe("typing name (pattern E)", () => {
  it.each([
    ["2x", ["2", "x"]],
    ["abcdefghi", ["a", "b", "c", "d", "e", "f", "g", "h", "i"]],
    ["a b", ["a", " ", "b"]],
  ])("types %s character by character", (text, chars) => {
    const { container } = render(
      <a href="/">
        <TypedText text={text} run="sign-in" />
      </a>,
    );
    expect(screen.getByTestId("typed-text").dataset.typing).toBe("type");
    expect(typedChars(container)).toEqual(chars);
    const indexes = [...container.querySelectorAll<HTMLElement>(".tx-type-char")].map((char) =>
      char.style.getPropertyValue("--tx-char"),
    );
    expect(indexes).toEqual(chars.map((_char, index) => String(index)));
    // The page holds the name once: the layer draws its characters with CSS only.
    expect(container.textContent).toBe(text);
    expect(screen.getByRole("link", { name: text })).toBeDefined();
  });

  it("types a letter with a combining accent as one character", () => {
    expect(typedCharacters("éx")).toEqual(["é", "x"]);
    expect(typedCharacters("")).toEqual([]);
  });

  it("falls back to code points where Intl.Segmenter is missing", () => {
    vi.stubGlobal("Intl", { ...Intl, Segmenter: undefined });
    try {
      expect(typedCharacters("2x")).toEqual(["2", "x"]);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("hides the typed layer from assistive technology and keeps the name as text", () => {
    const { container } = render(<TypedText text="abcdefghi" run="app" />);
    const layer = container.querySelector(".tx-type-layer");
    expect(layer?.getAttribute("aria-hidden")).toBe("true");
    expect(layer?.textContent).toBe("");
    const name = container.querySelector(".tx-type-text");
    expect(name?.textContent).toBe("abcdefghi");
    expect(name?.getAttribute("aria-hidden")).toBeNull();
  });

  it("reserves the full width with the name below the layer", () => {
    const { container } = render(<TypedText text="2x" run="sign-in" />);
    const wrapper = screen.getByTestId("typed-text");
    // The name is the first child and lies in the flow; the layer lies on top of it.
    expect(wrapper.firstElementChild?.className).toBe("tx-type-text");
    expect(wrapper.lastElementChild?.className).toBe("tx-type-layer");
    expect(container.querySelectorAll(".tx-type-text")).toHaveLength(1);
    expect(cssRule(".tx-type")).toMatch(/position: relative;/);
    expect(cssRule(".tx-type-text")).toMatch(/opacity: 0;/);
    expect(cssRule(".tx-type-layer")).toMatch(/position: absolute;\s+inset: 0;/);
  });

  it("types hard, about 120 ms per character after about 300 ms, in the interface font", () => {
    const wrapper = cssRule(".tx-type");
    expect(wrapper).toMatch(/--tx-type-start: 300ms;/);
    const step = Number(/--tx-type-step: (\d+)ms;/.exec(wrapper)?.[1]);
    expect(step).toBeGreaterThanOrEqual(110);
    expect(step).toBeLessThanOrEqual(130);
    expect(cssRule(".tx-type-char")).toMatch(/animation: tx-type-char 1ms step-end both;/);
    expect(cssRule(".tx-type-char:last-child::after")).toMatch(/animation: tx-type-blink 1\.8s step-end;/);
    expect(cssRule(".tx-type-layer::before,\n  .tx-type-char::after")).toMatch(/background: var\(--twox-brand\);/);
    expect(indexCss).not.toMatch(/\.tx-type[^{]*\{[^}]*font-family/);
  });

  it("types once per run and browser session", () => {
    const first = render(<TypedText text="2x" run="sign-in" />);
    expect(screen.getByTestId("typed-text").dataset.typing).toBe("type");
    expect(window.sessionStorage.getItem(TYPED_STORAGE_KEY)).toBe("sign-in");
    // Still typing on the same page, although the run is stored now.
    first.rerender(<TypedText text="2x" run="sign-in" />);
    expect(screen.getByTestId("typed-text").dataset.typing).toBe("type");
    first.unmount();

    // Next page load in the same session: the name stands still.
    const { container } = render(<TypedText text="2x" run="sign-in" />);
    expect(container.innerHTML).toBe("<span>2x</span>");
  });

  it("types again on the first page after signing in, once", () => {
    const { container, rerender, unmount } = render(<TypedText text="2x" run="sign-in" />);
    const signInLayer = container.querySelector(".tx-type-layer");
    rerender(<TypedText text="2x" run="app" />);
    // A new layer, so the animation starts again.
    const appLayer = container.querySelector(".tx-type-layer");
    expect(appLayer).not.toBeNull();
    expect(appLayer).not.toBe(signInLayer);
    expect(typedRuns()).toEqual(["sign-in", "app"]);
    // Signing out again: the sign-in page has typed already.
    rerender(<TypedText text="2x" run="sign-in" />);
    expect(container.querySelector(".tx-type")).toBeNull();
    unmount();

    expect(render(<TypedText text="2x" run="app" />).container.innerHTML).toBe("<span>2x</span>");
  });

  it("keeps the place of the name empty while the session loads, then types", () => {
    const { container, rerender } = render(<TypedText text="2x" run="pending" />);
    expect(screen.getByTestId("typed-text").dataset.typing).toBe("hidden");
    expect(container.querySelector(".tx-type-layer")).toBeNull();
    expect(container.textContent).toBe("2x");
    expect(typedRuns()).toEqual([]);
    rerender(<TypedText text="2x" run="sign-in" />);
    expect(screen.getByTestId("typed-text").dataset.typing).toBe("type");
  });

  it("shows the name at once while loading when this session has typed before", () => {
    markTyped("app");
    const { container } = render(<TypedText text="2x" run="pending" />);
    expect(container.innerHTML).toBe("<span>2x</span>");
  });

  it("shows the name at once when the user reduces motion, and does not type later in the session", () => {
    act(() => {
      updateDisplaySettings({ reduceMotion: true });
    });
    const { container } = render(<TypedText text="abcdefghi" run="sign-in" />);
    expect(container.innerHTML).toBe("<span>abcdefghi</span>");
    expect(animationClasses(container)).toEqual([]);
    // The run counts as done, so switching reduced motion off later does not start it.
    expect(typedRuns()).toEqual(["sign-in"]);
  });

  it("shows the name at once when the operating system asks for reduced motion", () => {
    fakeMatchMedia({ [reducedMotionQuery]: true });
    act(() => {
      refreshDisplay();
    });
    const { container } = render(<TypedText text="2x" run="app" />);
    expect(container.innerHTML).toBe("<span>2x</span>");
  });

  it("stops typing when reduced motion is switched on while the name types", () => {
    const { container } = render(<TypedText text="2x" run="sign-in" />);
    expect(animationClasses(container)).not.toEqual([]);
    act(() => {
      updateDisplaySettings({ reduceMotion: true });
    });
    expect(container.innerHTML).toBe("<span>2x</span>");
  });

  it("types without a usable storage and never fails", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(typedRuns()).toEqual([]);
    expect(() => {
      markTyped("sign-in");
    }).not.toThrow();
    render(<TypedText text="2x" run="sign-in" />);
    expect(screen.getByTestId("typed-text").dataset.typing).toBe("type");
  });

  it("ignores unknown values in the storage", () => {
    window.sessionStorage.setItem(TYPED_STORAGE_KEY, "other,app,,sign-in-x");
    expect(typedRuns()).toEqual(["app"]);
    markTyped("app");
    expect(window.sessionStorage.getItem(TYPED_STORAGE_KEY)).toBe("other,app,,sign-in-x");
  });
});
