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

describe("self-test layout in the page grid (work order 080)", () => {
  it("keeps heading and button in a narrow column and sets the cards in two or three columns on wide screens", async () => {
    loadSelftestMock.mockResolvedValueOnce({
      kind: "answered",
      selftest: {
        database: { ok: true, server_version: "18.7", error: "" },
        worker: { ok: true, result: "pong", error: "", duration_ms: 12 },
        ai: { enabled: false },
      },
    });
    render(<SelftestPage />);

    const cards = await screen.findByTestId("selftest-cards");
    const classes = cards.className.split(/\s+/);
    expect(classes).toEqual(expect.arrayContaining(["grid", "lg:grid-cols-2", "xl:grid-cols-3"]));
    // One column below 1024 px: no column count without a breakpoint.
    expect(classes.filter((name) => name.startsWith("grid-cols-"))).toEqual([]);
    expect([...cards.children].map((card) => card.getAttribute("data-testid"))).toEqual([
      "database-check",
      "worker-check",
      "ai-check",
    ]);
    expect(screen.getByTestId("selftest-head").className.split(/\s+/)).toContain("max-w-xl");
    // The page itself takes the whole grid; only the head stays narrow.
    expect(screen.getByTestId("selftest-page").className).not.toMatch(/max-w-/);
  });
});

describe("self-test status with icons (work order 071)", () => {
  it("shows each status as icon and text, never by colour alone", async () => {
    loadSelftestMock.mockResolvedValueOnce({
      kind: "answered",
      selftest: {
        database: { ok: true, server_version: "18.7", error: "" },
        worker: { ok: false, result: "", error: "No worker answered.", duration_ms: 5000 },
        ai: { enabled: false },
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

describe("AI card (E-59, work order 048)", () => {
  const base = {
    database: { ok: true, server_version: "18.7", error: "" },
    worker: { ok: true, result: "pong", error: "", duration_ms: 12 },
  };

  it("shows switched-off AI features as a neutral state, not as an error", async () => {
    loadSelftestMock.mockResolvedValueOnce({ kind: "answered", selftest: { ...base, ai: { enabled: false } } });
    render(<SelftestPage />);

    const card = await screen.findByTestId("ai-check");
    expect(screen.getByTestId("ai-heading").textContent).toBe("AI features");
    const status = screen.getByTestId("ai-status");
    expect(status.textContent).toBe("Not enabled");
    expect(status.querySelector("svg")?.getAttribute("data-icon")).toBe("info");
    expect(screen.getByTestId("ai-disabled").textContent).toBe(
      "AI features are not enabled. Everything else works without them, the keyword search included.",
    );
    // Neither error nor warning: no alert, no danger or warning colours, no warning sign.
    expect(screen.queryByRole("alert")).toBeNull();
    expect(card.className).not.toMatch(/danger|warning/);
    expect(status.className).not.toMatch(/danger|warning/);
    expect(card.querySelector('[data-icon="warning"], [data-icon="error"]')).toBeNull();
    expect(screen.queryByTestId("ai-error")).toBeNull();
  });

  it("shows model and dimensions when the AI check passed", async () => {
    loadSelftestMock.mockResolvedValueOnce({
      kind: "answered",
      selftest: { ...base, ai: { enabled: true, ok: true, model: "bge-m3", dimensions: 1024, error: "" } },
    });
    render(<SelftestPage />);

    expect((await screen.findByTestId("ai-status")).textContent).toBe("OK");
    expect(screen.getByTestId("ai-model").textContent).toBe("bge-m3");
    expect(screen.getByTestId("ai-dimensions").textContent).toBe("1,024");
    expect(screen.queryByTestId("ai-disabled")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the error when the AI features are on but the model service fails", async () => {
    loadSelftestMock.mockResolvedValueOnce({
      kind: "answered",
      selftest: {
        ...base,
        ai: {
          enabled: true,
          ok: false,
          model: "bge-m3",
          dimensions: 1024,
          error: "the model service refused the connection (is Ollama running?)",
        },
      },
    });
    render(<SelftestPage />);

    const status = await screen.findByTestId("ai-status");
    expect(status.textContent).toBe("Failed");
    expect(status.querySelector("svg")?.getAttribute("data-icon")).toBe("error");
    expect(screen.getByTestId("ai-error").textContent).toBe(
      "the model service refused the connection (is Ollama running?)",
    );
    expect(screen.getByTestId("ai-model").textContent).toBe("bge-m3");
    expect(screen.queryByTestId("ai-dimensions")).toBeNull();
  });

  it("shows no chat model fields when the AI features are off", async () => {
    loadSelftestMock.mockResolvedValueOnce({ kind: "answered", selftest: { ...base, ai: { enabled: false } } });
    render(<SelftestPage />);

    await screen.findByTestId("ai-check");
    expect(screen.queryByTestId("ai-chat-model")).toBeNull();
    expect(screen.queryByTestId("ai-chat-hint")).toBeNull();
    expect(screen.queryByTestId("ai-chat-error")).toBeNull();
  });

  it("is OK with a ready chat model", async () => {
    loadSelftestMock.mockResolvedValueOnce({
      kind: "answered",
      selftest: {
        ...base,
        ai: {
          enabled: true,
          ok: true,
          model: "bge-m3",
          dimensions: 1024,
          error: "",
          chat_model: "example-chat:8b",
          chat_ok: true,
          chat_error: "",
        },
      },
    });
    render(<SelftestPage />);

    const status = await screen.findByTestId("ai-status");
    expect(status.textContent).toBe("OK");
    expect(screen.getByTestId("ai-chat-model").textContent).toBe("example-chat:8b");
    expect(screen.getByTestId("ai-chat-status").textContent).toBe("ready");
    expect(screen.queryByTestId("ai-chat-hint")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("is OK with a quiet hint when no chat model is set yet", async () => {
    loadSelftestMock.mockResolvedValueOnce({
      kind: "answered",
      selftest: {
        ...base,
        ai: {
          enabled: true,
          ok: true,
          model: "bge-m3",
          dimensions: 1024,
          error: "",
          chat_model: "",
          chat_ok: false,
          chat_error: "chat model not configured",
        },
      },
    });
    render(<SelftestPage />);

    const card = await screen.findByTestId("ai-check");
    expect(screen.getByTestId("ai-status").textContent).toBe("OK");
    expect(screen.getByTestId("ai-chat-model").textContent).toBe("not set");
    const hint = screen.getByTestId("ai-chat-hint");
    expect(hint.textContent).toContain("Chat model not set yet.");
    // Quiet: no alert, no error text, no danger or warning colours.
    expect(screen.queryByRole("alert")).toBeNull();
    expect(hint.closest("[role=alert]")).toBeNull();
    expect(screen.queryByTestId("ai-chat-error")).toBeNull();
    expect(card.className).not.toMatch(/danger|warning/);
    expect(card.textContent).not.toContain("chat model not configured");
  });

  it("fails and shows the chat error when the chat model is not usable", async () => {
    loadSelftestMock.mockResolvedValueOnce({
      kind: "answered",
      selftest: {
        ...base,
        ai: {
          enabled: true,
          ok: true,
          model: "bge-m3",
          dimensions: 1024,
          error: "",
          chat_model: "example-chat:8b",
          chat_ok: false,
          chat_error: "model 'example-chat:8b' is not loaded in Ollama; load it with: ollama pull example-chat:8b",
        },
      },
    });
    render(<SelftestPage />);

    const status = await screen.findByTestId("ai-status");
    expect(status.textContent).toBe("Failed");
    expect(status.querySelector("svg")?.getAttribute("data-icon")).toBe("error");
    const error = screen.getByTestId("ai-chat-error");
    expect(error.getAttribute("role")).toBe("alert");
    expect(error.textContent).toBe(
      "model 'example-chat:8b' is not loaded in Ollama; load it with: ollama pull example-chat:8b",
    );
    // The embedding model itself is fine.
    expect(screen.getByTestId("ai-dimensions").textContent).toBe("1,024");
    expect(screen.queryByTestId("ai-error")).toBeNull();
    expect(screen.queryByTestId("ai-chat-hint")).toBeNull();
  });

  it("shows the chat model fields in German", async () => {
    await changeLanguage("de");
    loadSelftestMock.mockResolvedValueOnce({
      kind: "answered",
      selftest: {
        ...base,
        ai: {
          enabled: true,
          ok: true,
          model: "bge-m3",
          dimensions: 1024,
          error: "",
          chat_model: "",
          chat_ok: false,
          chat_error: "chat model not configured",
        },
      },
    });
    render(<SelftestPage />);

    expect((await screen.findByTestId("ai-chat-model")).textContent).toBe("nicht festgelegt");
    expect(screen.getByTestId("ai-chat-hint").textContent).toContain("Chat-Modell noch nicht festgelegt");
    expect(screen.getByTestId("ai-status").textContent).toBe("OK");
  });

  it("shows the neutral state in German", async () => {
    await changeLanguage("de");
    loadSelftestMock.mockResolvedValueOnce({ kind: "answered", selftest: { ...base, ai: { enabled: false } } });
    render(<SelftestPage />);

    expect((await screen.findByTestId("ai-status")).textContent).toBe("Nicht aktiviert");
    expect(screen.getByTestId("ai-heading").textContent).toBe("KI-Funktionen");
    expect(screen.getByTestId("ai-disabled").textContent).toContain("KI nicht aktiviert");
  });
});