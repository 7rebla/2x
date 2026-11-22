// Browser title per page (work order 078).
import { act, cleanup, render } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { pageTitle, usePageTitle } from "./usePageTitle.ts";

afterEach(async () => {
  cleanup();
  await changeLanguage("en");
  document.title = "";
});

function Page({ title }: { title: string | null }): ReactElement {
  usePageTitle(title);
  return <p>page</p>;
}

describe("pageTitle", () => {
  it("puts the page before the name of the application, separated by an en dash", () => {
    expect(pageTitle("2x", "Structure")).toBe("Structure – 2x");
    expect(pageTitle("2x", "  Test panel ")).toBe("Test panel – 2x");
  });

  it("is the name of the application alone without a page", () => {
    expect(pageTitle("2x", null)).toBe("2x");
    expect(pageTitle("2x", "   ")).toBe("2x");
  });
});

describe("usePageTitle", () => {
  it("sets the title while the page is shown and falls back to the name of the application afterwards", () => {
    const { rerender, unmount } = render(<Page title="Search" />);
    expect(document.title).toBe("Search – 2x");
    rerender(<Page title="Test panel" />);
    expect(document.title).toBe("Test panel – 2x");
    unmount();
    expect(document.title).toBe("2x");
  });

  it("leaves the title alone with null", () => {
    document.title = "Page not found – 2x";
    render(<Page title={null} />);
    expect(document.title).toBe("Page not found – 2x");
  });

  it("follows the language of the name of the application", async () => {
    render(<Page title="Suche" />);
    await act(async () => {
      await changeLanguage("de");
    });
    expect(document.title).toBe("Suche – 2x");
  });
});
