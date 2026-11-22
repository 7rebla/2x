import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeMatchMedia } from "../test/fakeMatchMedia.ts";
import { reducedMotionQuery } from "../theme/settings.ts";
import { refreshDisplay, updateDisplaySettings } from "../theme/store.ts";
import { AnimatedHeading, LoadingText, MaskedTitle } from "./TextMotion.tsx";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
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
    const heading = screen.getByRole("heading", { level: 2, name: "Standorte, Bereiche und Geräte" });
    expect(heading.textContent).toBe("Standorte, Bereiche und Geräte");
    expect(heading.classList.contains("tx-clear")).toBe(true);
    const words = heading.querySelectorAll<HTMLElement>(".tx-word");
    expect([...words].map((word) => word.textContent)).toEqual(["Standorte,", "Bereiche", "und", "Geräte"]);
    expect([...words].map((word) => word.style.getPropertyValue("--tx-index"))).toEqual(["0", "1", "2", "3"]);
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
