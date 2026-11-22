import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { loadSelftest } from "../api/selftest.ts";
import { changeLanguage } from "../i18n.ts";
import { SelftestPage } from "./SelftestPage.tsx";

vi.mock("../api/selftest.ts", () => ({ loadSelftest: vi.fn() }));

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

describe("self-test status with icons (work order 071)", () => {
  it("shows each status as icon and text, never by colour alone", async () => {
    loadSelftestMock.mockResolvedValueOnce({
      kind: "answered",
      selftest: {
        database: { ok: true, server_version: "18.7", error: "" },
        worker: { ok: false, result: "", error: "No worker answered.", duration_ms: 5000 },
      },
    });
    render(<SelftestPage />);

    const ok = await screen.findByTestId("database-status");
    expect(ok.textContent).toBe("OK");
    expect(ok.querySelector("svg")?.getAttribute("data-icon")).toBe("success");
    expect(ok.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
    const failed = screen.getByTestId("worker-status");
    expect(failed.textContent).toBe("Failed");
    expect(failed.querySelector("svg")?.getAttribute("data-icon")).toBe("error");
    expect(screen.getByRole("button", { name: "Check again" }).querySelector("svg")?.getAttribute("data-icon")).toBe("retry");
  });

  it("shows an error icon before the error text", async () => {
    loadSelftestMock.mockResolvedValueOnce({ kind: "unreachable" });
    render(<SelftestPage />);
    const error = await screen.findByTestId("selftest-error");
    expect(error.querySelector("svg")?.getAttribute("data-icon")).toBe("error");
    expect(error.textContent).toBe("The API did not respond. Is the server running?");
  });
});
