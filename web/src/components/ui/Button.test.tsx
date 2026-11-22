import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Button } from "./Button.tsx";
import { buttonClasses, buttonVariants, controlSizes } from "./classes.ts";

afterEach(() => {
  cleanup();
});

function iconsOf(button: HTMLElement): (string | null)[] {
  return [...button.querySelectorAll("svg")].map((svg) => svg.getAttribute("data-icon"));
}

describe("Button", () => {
  it("renders a native button with the given type and label", () => {
    render(<Button type="submit">Save</Button>);
    const button = screen.getByRole("button", { name: "Save" });
    expect(button.tagName).toBe("BUTTON");
    expect(button.getAttribute("type")).toBe("submit");
    expect(button.getAttribute("aria-busy")).toBeNull();
    expect((button as HTMLButtonElement).disabled).toBe(false);
  });

  it("requires a type", () => {
    // @ts-expect-error -- every button states its type
    render(<Button>Untyped</Button>);
  });

  it.each(buttonVariants.flatMap((variant) => controlSizes.map((size) => [variant, size] as const)))(
    "uses the classes of variant %s in size %s",
    (variant, size) => {
      render(
        <Button type="button" variant={variant} size={size}>
          Label
        </Button>,
      );
      expect(screen.getByRole("button").className).toBe(buttonClasses(variant, size));
    },
  );

  it("is secondary and md by default", () => {
    render(<Button type="button">Label</Button>);
    expect(screen.getByRole("button").className).toBe(buttonClasses("secondary", "md"));
  });

  it("has one height per size and the same disabled look in every variant", () => {
    for (const variant of buttonVariants) {
      expect(buttonClasses(variant, "md")).toContain("min-h-9");
      expect(buttonClasses(variant, "sm")).toContain("min-h-7");
      expect(buttonClasses(variant, "md")).toContain("disabled:opacity-50");
      expect(buttonClasses(variant, "md")).toContain("disabled:cursor-not-allowed");
      // A border in every variant, so all variants of one size have the same box.
      expect(buttonClasses(variant, "md")).toMatch(/\bborder\b/);
    }
  });

  it("adds layout classes of the caller after its own", () => {
    render(
      <Button type="button" className="self-center">
        Label
      </Button>,
    );
    expect(screen.getByRole("button").className.endsWith(" self-center")).toBe(true);
  });

  it("shows a decorative icon before the label (20 px in md, 16 px in sm)", () => {
    render(
      <>
        <Button type="button" icon="filter">
          Apply
        </Button>
        <Button type="button" size="sm" icon="edit">
          Edit
        </Button>
      </>,
    );
    const apply = screen.getByRole("button", { name: "Apply" });
    const svg = apply.querySelector("svg");
    expect(svg?.getAttribute("data-icon")).toBe("filter");
    expect(svg?.getAttribute("aria-hidden")).toBe("true");
    expect(svg?.getAttribute("width")).toBe("20");
    expect(apply.firstElementChild).toBe(svg);
    expect(screen.getByRole("button", { name: "Edit" }).querySelector("svg")?.getAttribute("width")).toBe("16");
  });

  it("shows the icon after the label when asked", () => {
    render(
      <Button type="button" icon="next" iconPosition="end">
        Next
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Next" });
    expect(button.lastElementChild?.getAttribute("data-icon")).toBe("next");
    expect(button.textContent).toBe("Next");
  });

  it("keeps an aria-label of the caller as accessible name", () => {
    render(
      <Button type="button" icon="edit" aria-label="Edit Test device">
        Edit
      </Button>,
    );
    expect(screen.getByRole("button", { name: "Edit Test device" })).not.toBeNull();
  });

  it("is disabled and does not react to clicks", () => {
    const onClick = vi.fn();
    render(
      <Button type="button" disabled onClick={onClick}>
        Previous
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Previous" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("calls onClick while enabled", () => {
    const onClick = vi.fn();
    render(
      <Button type="button" onClick={onClick}>
        Next
      </Button>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("while loading: disabled, busy, the turning loading icon in place of its icon, the caller's label", () => {
    const onClick = vi.fn();
    render(
      <Button type="submit" variant="primary" icon="upload" loading onClick={onClick}>
        Uploading…
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Uploading…" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    expect(button.getAttribute("aria-busy")).toBe("true");
    expect(iconsOf(button)).toEqual(["loading"]);
    expect(button.querySelector("svg")?.getAttribute("class")).toContain("animate-spin");
    expect(button.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("shows the loading icon at the start also for a button without icon or with the icon at the end", () => {
    render(
      <>
        <Button type="submit" loading>
          Saving…
        </Button>
        <Button type="button" icon="next" iconPosition="end" loading>
          Next
        </Button>
      </>,
    );
    for (const name of ["Saving…", "Next"]) {
      const button = screen.getByRole("button", { name });
      expect(iconsOf(button)).toEqual(["loading"]);
      expect(button.firstElementChild?.getAttribute("data-icon")).toBe("loading");
    }
  });

  it("passes the ref and other attributes on", () => {
    const ref = createRef<HTMLButtonElement>();
    render(
      <Button ref={ref} type="button" aria-expanded={false} data-testid="menu">
        Menu
      </Button>,
    );
    expect(ref.current).toBe(screen.getByTestId("menu"));
    expect(ref.current?.getAttribute("aria-expanded")).toBe("false");
  });
});
