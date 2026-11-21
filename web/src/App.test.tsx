import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { App } from "./App.tsx";

afterEach(() => {
  cleanup();
});

describe("App", () => {
  it("renders the heading", () => {
    render(<App />);

    const heading = screen.getByRole("heading", { level: 1, name: "2x" });

    expect(heading.textContent).toBe("2x");
  });

  it("renders the placeholder hint", () => {
    render(<App />);

    expect(screen.getByText(/placeholder/i).tagName).toBe("P");
  });
});
