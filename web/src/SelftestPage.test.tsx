import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { loadSelftest } from "./api/selftest.ts";
import { SelftestPage } from "./SelftestPage.tsx";
import { texts } from "./texts.ts";

vi.mock("./api/selftest.ts", () => ({ loadSelftest: vi.fn() }));

const loadSelftestMock = vi.mocked(loadSelftest);

afterEach(() => {
  cleanup();
  loadSelftestMock.mockReset();
});

describe("self-test page with a failing loader", () => {
  it("shows an error instead of loading forever when loadSelftest throws, and can check again", async () => {
    loadSelftestMock
      .mockRejectedValueOnce(new TypeError("AbortSignal.any is not a function"))
      .mockResolvedValueOnce({ kind: "unreachable" });
    render(<SelftestPage />);

    const error = await screen.findByTestId("selftest-error");
    expect(error.textContent).toBe(texts.selftest.unexpectedError);
    expect(error.textContent).not.toContain("AbortSignal");
    expect(screen.queryByTestId("selftest-loading")).toBeNull();

    const button = screen.getByRole("button", { name: texts.selftest.recheck });
    expect(button.hasAttribute("disabled")).toBe(false);
    fireEvent.click(button);

    expect((await screen.findByTestId("selftest-error")).textContent).toBe(
      texts.selftest.apiUnreachable,
    );
    expect(loadSelftestMock).toHaveBeenCalledTimes(2);
  });
});
