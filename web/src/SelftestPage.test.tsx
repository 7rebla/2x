import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { loadSelftest } from "./api/selftest.ts";
import { SelftestPage } from "./SelftestPage.tsx";
import { changeLanguage } from "./i18n.ts";

vi.mock("./api/selftest.ts", () => ({ loadSelftest: vi.fn() }));

const loadSelftestMock = vi.mocked(loadSelftest);

afterEach(async () => {
  cleanup();
  loadSelftestMock.mockReset();
  await changeLanguage("en");
  window.localStorage.clear();
});

describe("self-test page with a failing loader", () => {
  it("shows an error instead of loading forever when loadSelftest throws, and can check again", async () => {
    loadSelftestMock
      .mockRejectedValueOnce(new TypeError("AbortSignal.any is not a function"))
      .mockResolvedValueOnce({ kind: "unreachable" });
    render(<SelftestPage />);

    const error = await screen.findByTestId("selftest-error");
    expect(error.textContent).toBe("The self-test could not be run in this browser. Please try again.");
    expect(error.textContent).not.toContain("AbortSignal");
    expect(screen.queryByTestId("selftest-loading")).toBeNull();

    const button = screen.getByRole("button", { name: "Check again" });
    expect(button.hasAttribute("disabled")).toBe(false);
    fireEvent.click(button);

    expect((await screen.findByTestId("selftest-error")).textContent).toBe(
      "The API did not respond. Is the server running?",
    );
    expect(loadSelftestMock).toHaveBeenCalledTimes(2);
  });
});
