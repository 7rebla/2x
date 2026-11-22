// Answer page (work order 132): form and ?q=, the states of an answer
// (streaming, answered, no evidence, contradiction, AI off, failure), links
// from source numbers to checked sources only, the answer as plain text.
// The stream comes from a fetch stub with a ReadableStream (test/fakeApi.ts);
// every question, answer and section text here is a test sentence.
import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { AnswerSource, AnswerStatus } from "../api/generated";
import { changeLanguage } from "../i18n.ts";
import { fakeApi, fakeEventStream, type Handler, jsonResponse, reader } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";
import { answerLocation, answerSource, deltaEvent, doneEvent, errorEvent, sourcesEvent } from "./answer/testData.ts";
import { fakeStructureApi } from "./structure/testData.ts";

const STATUS_PATH = "/api/v1/answers/status/";
const ANSWERS_PATH = "/api/v1/answers/";
const AVAILABLE: AnswerStatus = { enabled: true, chat_model_configured: true, available: true };

beforeAll(async () => {
  await import("./AnswerPage.tsx");
});

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

/**
 * A server with the given status; the answer stream is driven by the test
 * unless `answer` is given. Devices and plants come from the test structure
 * (structure/testData.ts) for the choice of the limit (work order 133).
 */
function fakeAnswerServer(status: AnswerStatus = AVAILABLE, answer?: Handler) {
  const stream = fakeEventStream();
  const structure = fakeStructureApi();
  const api = fakeApi(reader, (request) => {
    const path = new URL(request.url).pathname;
    if (path === STATUS_PATH) {
      return jsonResponse(status);
    }
    if (path === ANSWERS_PATH) {
      return answer === undefined ? stream.response(request) : answer(request);
    }
    return structure.handler(request);
  });
  return { stream, posts: () => api.requestsTo(ANSWERS_PATH) };
}

function askButton(name = "Ask"): HTMLButtonElement {
  const button = screen.getByRole("button", { name });
  if (!(button instanceof HTMLButtonElement)) {
    throw new Error("not a button");
  }
  return button;
}

async function questionField(label = "Question"): Promise<HTMLTextAreaElement> {
  const field = await screen.findByLabelText(label);
  if (!(field instanceof HTMLTextAreaElement)) {
    throw new Error("not a text area");
  }
  return field;
}

/** Types `text` and presses "Ask" once the status allows it. */
async function ask(text = "Test question about the inspection?", button = "Ask", label = "Question"): Promise<void> {
  fireEvent.change(await questionField(label), { target: { value: text } });
  await waitFor(() => {
    expect(askButton(button).disabled).toBe(false);
  });
  fireEvent.click(askButton(button));
}

function statusLine(): string {
  return screen.getByRole("status").textContent;
}

async function answerCard(): Promise<HTMLElement> {
  return screen.findByRole("article", { name: "Answer" });
}

function card(n: number): HTMLElement {
  const found = document.getElementById(`source-${String(n)}`);
  if (found === null) {
    throw new Error(`no card for source ${String(n)}`);
  }
  return found;
}

/** Source 1 on page 14, source 2 on pages 3–4, source 3 not cited. */
const SOURCES: AnswerSource[] = [
  answerSource(1, { page_start: 14, page_end: 14 }),
  answerSource(2),
  answerSource(3, { snippet: "Test sentence that the answer does not cite." }),
];

describe("form", () => {
  it("shows heading, labelled form and an empty status region", async () => {
    fakeAnswerServer();
    renderApp("/ask");

    expect((await screen.findByRole("heading", { level: 1 })).textContent).toBe("Ask");
    expect(document.title).toBe("Ask – 2x");
    expect(screen.getByRole("form", { name: "Ask a question" })).toBeDefined();
    expect((await questionField()).value).toBe("");
    expect(statusLine()).toBe("");
    // Nothing to send yet.
    expect(askButton().disabled).toBe(true);
    expect(screen.queryByTestId("answer-cancel")).toBeNull();
  });

  it("fills the field from ?q= without sending it", async () => {
    const server = fakeAnswerServer();
    renderApp("/ask?q=Test%20question%20from%20a%20link");

    expect((await questionField()).value).toBe("Test question from a link");
    await waitFor(() => {
      expect(askButton().disabled).toBe(false);
    });
    expect(server.posts()).toHaveLength(0);
    expect(statusLine()).toBe("");
  });

  it("sends with the button or Ctrl+Enter, not with Enter alone, and only the question in the body", async () => {
    const server = fakeAnswerServer();
    renderApp("/ask");
    const field = await questionField();
    fireEvent.change(field, { target: { value: "  Test question?  " } });
    await waitFor(() => {
      expect(askButton().disabled).toBe(false);
    });

    fireEvent.keyDown(field, { key: "Enter" });
    expect(server.posts()).toHaveLength(0);

    fireEvent.keyDown(field, { key: "Enter", ctrlKey: true });
    await waitFor(() => {
      expect(server.posts()).toHaveLength(1);
    });
    const [request] = server.posts();
    expect(request?.method).toBe("POST");
    expect(new URL(request?.url ?? "").search).toBe("");
    expect(await request?.json()).toEqual({ question: "Test question?" });
  });

  it("counts the characters and blocks a question over 500 characters", async () => {
    fakeAnswerServer();
    renderApp("/ask");
    const field = await questionField();
    fireEvent.change(field, { target: { value: "x".repeat(500) } });
    await waitFor(() => {
      expect(askButton().disabled).toBe(false);
    });
    expect(screen.getByTestId("answer-length").textContent).toBe("500 of 500 characters");

    fireEvent.change(field, { target: { value: "x".repeat(501) } });
    expect(screen.getByTestId("answer-length").textContent).toBe("At most 500 characters – please shorten the question.");
    expect(field.getAttribute("aria-invalid")).toBe("true");
    expect(askButton().disabled).toBe(true);
  });
});

describe("streaming", () => {
  it("shows the growing text busy and without links, with Cancel", async () => {
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask();

    await waitFor(() => {
      expect(statusLine()).toBe("Searching for sources…");
    });
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDefined();

    stream.send(sourcesEvent(SOURCES) + deltaEvent("Provisional text [1]"));
    const article = await answerCard();
    await waitFor(() => {
      expect(statusLine()).toBe("Writing the answer…");
    });
    expect(article.getAttribute("aria-busy")).toBe("true");
    expect(article.hasAttribute("aria-live")).toBe(false);
    expect(within(article).getByTestId("answer-text").textContent).toBe("Provisional text [1]");
    expect(within(article).queryAllByRole("link")).toHaveLength(0);
    // No source list before the answer is checked.
    expect(screen.queryByRole("list", { name: "Sources" })).toBeNull();

    stream.send(deltaEvent(" grows [2]."));
    await waitFor(() => {
      expect(within(article).getByTestId("answer-text").textContent).toBe("Provisional text [1] grows [2].");
    });
    expect(within(article).queryAllByRole("link")).toHaveLength(0);
  });

  it("cancels: the text stays, marked as not checked", async () => {
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask();
    stream.send(sourcesEvent(SOURCES) + deltaEvent("Unfinished text [1]"));
    await answerCard();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => {
      expect(statusLine()).toBe("Cancelled");
    });
    const article = await answerCard();
    expect(article.getAttribute("aria-busy")).toBe("false");
    expect(within(article).getByText("Cancelled – this text was not checked.")).toBeDefined();
    expect(within(article).queryAllByRole("link")).toHaveLength(0);
    expect(screen.queryByTestId("answer-cancel")).toBeNull();
    expect(stream.stopped).toBe(true);
  });
});

describe("answered", () => {
  it("replaces the streamed text and links checked numbers to their sources", async () => {
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask();
    stream.send(sourcesEvent(SOURCES) + deltaEvent("Streamed text [1]"));
    await answerCard();
    stream.send(doneEvent({ cited: [1, 2], final_text: "Checked text [1]. Second sentence [2]. Unknown [9]." }));
    stream.close();

    await waitFor(() => {
      expect(statusLine()).toBe("Done");
    });
    const article = await answerCard();
    expect(article.getAttribute("aria-busy")).toBe("false");
    expect(within(article).getByTestId("answer-text").textContent).toBe(
      "Checked text [1]. Second sentence [2]. Unknown [9].",
    );
    expect(within(article).getByText("Answer with checked sources")).toBeDefined();

    const links = within(article).getAllByRole("link");
    expect(links.map((link) => link.getAttribute("aria-label"))).toEqual([
      "Source 1: Test manual, page 14",
      "Source 2: Test manual, pages 3–4",
    ]);
    expect(links.map((link) => link.getAttribute("href"))).toEqual(["#source-1", "#source-2"]);
    // [9] is no source of the answer: plain text.
    expect(within(article).queryByRole("link", { name: /9/ })).toBeNull();
    expect(screen.queryByTestId("answer-note")).toBeNull();

    const list = screen.getByRole("list", { name: "Sources" });
    expect(list.tagName).toBe("OL");
    const cards = within(list).getAllByTestId("answer-source");
    expect(cards.map((item) => item.dataset.n)).toEqual(["1", "2"]);
    expect(within(card(1)).getByTestId("search-hit-page").textContent).toBe("p. 14");
    expect(within(card(2)).getByTestId("search-hit-page").textContent).toBe("pp. 3–4");
    expect(within(card(2)).getByTestId("search-hit-heading-path").textContent).toBe("Section: Maintenance › Inspection");
    expect(within(card(2)).getByTestId("search-snippet").textContent).toBe("Test sentence of section 2.");
    expect(within(card(2)).getByTestId("search-location-document").getAttribute("href")).toBe("/documents/7");
    expect(within(card(2)).getByTestId("search-location-device").getAttribute("href")).toBe("/devices/1000");
    expect(within(card(2)).getByTestId("search-location-plant").textContent).toContain("Test plant one");

    fireEvent.click(links[1] ?? article);
    expect(document.activeElement).toBe(card(2));
  });

  it("names the citations in German", async () => {
    await changeLanguage("de");
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask("Testfrage?", "Fragen", "Frage");
    stream.send(sourcesEvent(SOURCES));
    stream.send(doneEvent({ cited: [1, 2], final_text: "Geprüfter Text [1] [2]." }));
    stream.close();

    const article = await screen.findByRole("article", { name: "Antwort" });
    await waitFor(() => {
      expect(within(article).getAllByRole("link")).toHaveLength(2);
    });
    expect(within(article).getAllByRole("link").map((link) => link.getAttribute("aria-label"))).toEqual([
      "Quelle 1: Test manual, Seite 14",
      "Quelle 2: Test manual, Seiten 3–4",
    ]);
    expect(screen.getByRole("list", { name: "Quellen" })).toBeDefined();
    expect(statusLine()).toBe("Fertig");
  });

  it("marks removed statements", async () => {
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask();
    stream.send(sourcesEvent(SOURCES));
    stream.send(doneEvent({ cited: [1], removed_sentences: 2, final_text: "Kept sentence [1]." }));
    stream.close();

    const note = await screen.findByTestId("answer-note");
    expect(note.textContent).toBe("Statements without evidence were removed.");
  });

  it("keeps markup in the answer as text", async () => {
    const markup = '<img src=x onerror="alert(1)"> <a href="https://example.invalid/">click</a> https://example.invalid/';
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask();
    stream.send(sourcesEvent(SOURCES) + deltaEvent(markup));
    const streaming = await answerCard();
    await waitFor(() => {
      expect(within(streaming).getByTestId("answer-text").textContent).toBe(markup);
    });
    expect(streaming.querySelector("img")).toBeNull();
    expect(streaming.querySelector("a")).toBeNull();

    stream.send(doneEvent({ cited: [1], final_text: `${markup} [1]` }));
    stream.close();
    await waitFor(() => {
      expect(statusLine()).toBe("Done");
    });
    const article = await answerCard();
    expect(within(article).getByTestId("answer-text").textContent).toBe(`${markup} [1]`);
    expect(article.querySelector("img")).toBeNull();
    const anchors = [...article.querySelectorAll("a")];
    expect(anchors.map((anchor) => anchor.getAttribute("href"))).toEqual(["#source-1"]);
  });

  it("does not link a source without page and heading path, but a Markdown source with headings", async () => {
    const sources = [
      answerSource(1, { page_start: null, page_end: null, heading_path: [] }),
      answerSource(2, {
        page_start: null,
        page_end: null,
        heading_path: ["Setup", "Network"],
        locations: [answerLocation({ document_title: "Test notes", version_filename: "test-notes.md" })],
      }),
    ];
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask();
    stream.send(sourcesEvent(sources));
    stream.send(doneEvent({ cited: [1, 2], final_text: "First [1]. Second [2]." }));
    stream.close();

    await waitFor(() => {
      expect(statusLine()).toBe("Done");
    });
    const article = await answerCard();
    const links = within(article).getAllByRole("link");
    expect(links.map((link) => link.getAttribute("aria-label"))).toEqual(["Source 2: Test notes, Setup › Network"]);
    expect(within(card(1)).getByTestId("answer-source-without-page").textContent).toBe("Place without a page");
    expect(within(card(2)).queryByTestId("answer-source-without-page")).toBeNull();
    expect(within(card(2)).queryByTestId("search-hit-page")).toBeNull();
  });
});

describe("end states", () => {
  it("no evidence: the fixed sentence of the catalog, no sources, a link to the search", async () => {
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask("Test question without evidence?");
    stream.send(sourcesEvent(SOURCES));
    stream.send(doneEvent({ status: "no_evidence", cited: [], final_text: "Server text in another language." }));
    stream.close();

    const box = await screen.findByTestId("answer-no-evidence");
    expect(box.textContent).toContain("I can't find anything on this in the documents.");
    expect(box.textContent).not.toContain("Server text");
    expect(box.querySelector("svg")).not.toBeNull();
    expect(screen.queryByRole("list", { name: "Sources" })).toBeNull();
    expect(screen.queryByTestId("answer-source")).toBeNull();
    expect(within(box).getByRole("link", { name: "Search the documents for this question" }).getAttribute("href")).toBe(
      "/search?q=Test+question+without+evidence%3F",
    );
  });

  it("contradiction: notice, and both sources marked with a text", async () => {
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask();
    stream.send(sourcesEvent(SOURCES));
    stream.send(
      doneEvent({ status: "contradiction", cited: [1, 2], final_text: "The documents contradict each other: [1] [2]." }),
    );
    stream.close();

    const notice = await screen.findByTestId("answer-contradiction");
    expect(notice.textContent).toBe("The documents contradict each other. Compare the marked places.");
    expect(notice.querySelector("svg")).not.toBeNull();
    for (const n of [1, 2]) {
      expect(card(n).dataset.contradicting).toBe("true");
      expect(within(card(n)).getByTestId("answer-source-contradiction").textContent).toBe("Contradicting place");
    }
    expect(within(await answerCard()).getAllByRole("link")).toHaveLength(2);
  });

  it.each([
    [{ enabled: false, chat_model_configured: true, available: false }, "off", "The AI features are switched off"],
    [{ enabled: true, chat_model_configured: false, available: false }, "unavailable", "Answers are not available"],
    [{ enabled: true, chat_model_configured: true, available: false }, "unavailable", "Answers are not available"],
  ])("AI not usable (%o): a calm hint with a link to the search, the form disabled", async (status, kind, text) => {
    const server = fakeAnswerServer(status);
    renderApp("/ask?q=Test%20question");

    const notice = await screen.findByTestId("answer-unavailable");
    expect(notice.dataset.availability).toBe(kind);
    expect(notice.textContent).toContain(text);
    expect(notice.getAttribute("role")).toBeNull();
    expect(within(notice).getByRole("link", { name: "Go to the search" }).getAttribute("href")).toBe("/search");
    expect((await questionField()).disabled).toBe(true);
    expect(askButton().disabled).toBe(true);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(server.posts()).toHaveLength(0);
  });

  it("AI switched off between status and question (409): the same hint", async () => {
    fakeAnswerServer(AVAILABLE, () =>
      jsonResponse({ detail: "AI features are switched off.", code: "ai_disabled" }, 409),
    );
    renderApp("/ask");
    await ask();

    const notice = await screen.findByTestId("answer-unavailable");
    expect(notice.dataset.availability).toBe("off");
    expect((await questionField()).disabled).toBe(true);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("an error event: role=alert with the fixed text of its code", async () => {
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask();
    stream.send(sourcesEvent(SOURCES) + deltaEvent("Partial [1]"));
    stream.send(errorEvent("timeout", "Raw server text."));
    stream.close();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("The answer took too long.");
    expect(alert.textContent).toContain("Code: timeout");
    expect(alert.textContent).not.toContain("Raw server text.");
    expect(screen.queryByRole("article")).toBeNull();
    // The form is free again.
    expect(askButton().disabled).toBe(false);
  });

  it("a stream that breaks off: role=alert", async () => {
    const { stream } = fakeAnswerServer();
    renderApp("/ask");
    await ask();
    stream.send(sourcesEvent(SOURCES));
    stream.close();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("The connection broke off before the answer was complete.");
  });

  it("a rejected question (400): ErrorMessage with status and the text of the API", async () => {
    fakeAnswerServer(AVAILABLE, () => jsonResponse({ question: ["Ensure this field has no more than 500 characters."] }, 400));
    renderApp("/ask");
    await ask();

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByTestId("error-summary").textContent).toContain("400");
    expect(statusLine()).toBe("");
  });
});

describe("limit to one device or one plant (work order 133)", () => {
  function choice(testId: "answer-device" | "answer-plant"): HTMLSelectElement {
    const select = screen.getByTestId(testId);
    if (!(select instanceof HTMLSelectElement)) {
      throw new Error("not a choice");
    }
    return select;
  }

  /** Waits until both lists are loaded (the test structure has device 1003 and plant 102). */
  async function listsLoaded(): Promise<void> {
    await waitFor(() => {
      expect(within(choice("answer-device")).queryByRole("option", { name: "Test drive (test-drive-1)" })).not.toBeNull();
      expect(
        within(choice("answer-plant")).queryByRole("option", { name: "Test plant three (test-plant-3)" }),
      ).not.toBeNull();
    });
  }

  function chip(): HTMLElement | null {
    return screen.queryByTestId("answer-scope");
  }

  it("offers all devices grouped by plant and all plants sorted by name, with labels", async () => {
    fakeAnswerServer();
    renderApp("/ask");
    await listsLoaded();

    expect(screen.getByLabelText("Device")).toBe(choice("answer-device"));
    expect(choice("answer-device").value).toBe("");
    expect(
      Array.from(choice("answer-device").querySelectorAll("optgroup")).map((group) => [
        group.label,
        Array.from(group.querySelectorAll("option")).map((option) => option.textContent),
      ]),
    ).toEqual([
      ["Test plant one", ["Test controller (test-plc-1)", "Test panel (test-hmi-1)", "Test remote I/O (test-io-1)"]],
      ["Test plant three", ["Test drive (test-drive-1)"]],
    ]);
    expect(screen.getByLabelText("Plant")).toBe(choice("answer-plant"));
    expect(Array.from(choice("answer-plant").options).map((option) => option.textContent)).toEqual([
      "All plants",
      "Test plant one (test-plant-1)",
      "Test plant three (test-plant-3)",
      "Test plant two (test-plant-2)",
    ]);
    expect(chip()).toBeNull();
  });

  it("takes ?device= into the choice and the chip and lifts it again", async () => {
    fakeAnswerServer();
    const { router } = renderApp("/ask?device=1000");
    await listsLoaded();

    expect(choice("answer-device").value).toBe("1000");
    expect(choice("answer-plant").value).toBe("");
    await waitFor(() => {
      expect(chip()?.textContent).toContain("Limited to: device Test controller (test-plc-1)");
    });
    expect(chip()?.getAttribute("role")).toBeNull();

    // Label in name: the button is named by its visible text alone.
    const reset = screen.getByRole("button", { name: "Remove limit" });
    expect(reset.getAttribute("aria-label")).toBeNull();
    fireEvent.click(reset);
    await waitFor(() => {
      expect(chip()).toBeNull();
    });
    expect(router.state.location.search).toBe("");
    expect(choice("answer-device").value).toBe("");
  });

  it("takes ?plant= into the choice and the chip; lifting it keeps ?q=", async () => {
    const server = fakeAnswerServer();
    const { router } = renderApp("/ask?q=Test%20question&plant=102");
    await listsLoaded();

    expect(choice("answer-plant").value).toBe("102");
    expect(choice("answer-device").value).toBe("");
    expect(screen.getByTestId("answer-scope-name").textContent).toBe("Test plant three");
    expect(chip()?.textContent).toContain("Limited to: plant Test plant three");

    fireEvent.click(screen.getByTestId("answer-scope-reset"));
    await waitFor(() => {
      expect(chip()).toBeNull();
    });
    expect(router.state.location.search).toBe("?q=Test+question");
    expect((await questionField()).value).toBe("Test question");
    expect(server.posts()).toHaveLength(0);
  });

  it("shows the chip in German", async () => {
    await changeLanguage("de");
    fakeAnswerServer();
    renderApp("/ask?device=1003");
    await waitFor(() => {
      expect(chip()?.textContent).toContain("Eingegrenzt auf: Gerät Test drive (test-drive-1)");
    });
    expect(screen.getByTestId("answer-scope-reset").textContent).toBe("Eingrenzung aufheben");
  });

  it.each([
    ["/ask?device=1000", { device: [1000] }, "?device=1000"],
    ["/ask?plant=100", { plant: [100] }, "?plant=100"],
    ["/ask", {}, ""],
  ])("%s sends the limit in the body and never the question in the address", async (path, limit, search) => {
    const server = fakeAnswerServer();
    const { router } = renderApp(path);
    await listsLoaded();
    await ask("Test question about the limit?");

    await waitFor(() => {
      expect(server.posts()).toHaveLength(1);
    });
    expect(await server.posts()[0]?.json()).toEqual({ question: "Test question about the limit?", ...limit });
    expect(new URL(server.posts()[0]?.url ?? "").search).toBe("");
    expect(router.state.location.search).toBe(search);
    expect(router.state.location.search).not.toContain("question");
  });

  it("a chosen device replaces the address without sending, and goes into the next question", async () => {
    const server = fakeAnswerServer();
    const { router } = renderApp("/ask");
    await listsLoaded();

    fireEvent.change(choice("answer-device"), { target: { value: "1001" } });
    await waitFor(() => {
      expect(router.state.location.search).toBe("?device=1001");
    });
    expect(router.state.historyAction).toBe("REPLACE");
    expect(server.posts()).toHaveLength(0);
    expect(chip()?.textContent).toContain("Test panel (test-hmi-1)");

    await ask("Test question about the panel?");
    await waitFor(() => {
      expect(server.posts()).toHaveLength(1);
    });
    expect(await server.posts()[0]?.json()).toEqual({ question: "Test question about the panel?", device: [1001] });
    expect(router.state.location.search).toBe("?device=1001");
  });

  it("device and plant exclude each other", async () => {
    fakeAnswerServer();
    const { router } = renderApp("/ask?device=1000");
    await listsLoaded();

    fireEvent.change(choice("answer-plant"), { target: { value: "100" } });
    await waitFor(() => {
      expect(router.state.location.search).toBe("?plant=100");
    });
    expect(choice("answer-device").value).toBe("");
    expect(choice("answer-plant").value).toBe("100");

    fireEvent.change(choice("answer-device"), { target: { value: "1003" } });
    await waitFor(() => {
      expect(router.state.location.search).toBe("?device=1003");
    });
    expect(choice("answer-plant").value).toBe("");
    expect(choice("answer-device").value).toBe("1003");

    fireEvent.change(choice("answer-device"), { target: { value: "" } });
    await waitFor(() => {
      expect(router.state.location.search).toBe("");
    });
    expect(chip()).toBeNull();
  });

  it("with both in the address the device wins, and only the device is sent", async () => {
    const server = fakeAnswerServer();
    renderApp("/ask?device=1000&plant=102");
    await listsLoaded();
    expect(choice("answer-device").value).toBe("1000");
    expect(choice("answer-plant").value).toBe("");

    await ask();
    await waitFor(() => {
      expect(server.posts()).toHaveLength(1);
    });
    expect(await server.posts()[0]?.json()).toEqual({ question: "Test question about the inspection?", device: [1000] });
  });

  it.each(["/ask?device=abc", "/ask?device=0", "/ask?plant=-1", "/ask?device=1.5"])(
    "%s counts as all devices",
    async (path) => {
      const server = fakeAnswerServer();
      renderApp(path);
      await listsLoaded();
      expect(choice("answer-device").value).toBe("");
      expect(choice("answer-plant").value).toBe("");
      expect(chip()).toBeNull();

      await ask();
      await waitFor(() => {
        expect(server.posts()).toHaveLength(1);
      });
      expect(await server.posts()[0]?.json()).toEqual({ question: "Test question about the inspection?" });
    },
  );

  it("an unknown device id stays as its own entry and in the chip, and is sent", async () => {
    const server = fakeAnswerServer();
    renderApp("/ask?device=999");
    await listsLoaded();

    await waitFor(() => {
      expect(choice("answer-device").value).toBe("999");
    });
    expect(choice("answer-device").selectedOptions[0]?.textContent).toBe("Unknown device (999)");
    expect(screen.getByTestId("answer-scope-name").textContent).toBe("Unknown device (999)");

    await ask();
    await waitFor(() => {
      expect(server.posts()).toHaveLength(1);
    });
    expect(await server.posts()[0]?.json()).toEqual({ question: "Test question about the inspection?", device: [999] });
  });

  it("an unknown plant id stays as its own entry and in the chip", async () => {
    fakeAnswerServer();
    renderApp("/ask?plant=998");
    await listsLoaded();

    await waitFor(() => {
      expect(choice("answer-plant").value).toBe("998");
    });
    expect(choice("answer-plant").selectedOptions[0]?.textContent).toBe("Unknown plant (998)");
    expect(screen.getByTestId("answer-scope-name").textContent).toBe("Unknown plant (998)");
  });

  it("lifting the limit does not stop a running answer", async () => {
    const { stream, posts } = fakeAnswerServer();
    const { router } = renderApp("/ask?device=1000");
    await listsLoaded();
    await ask();
    stream.send(sourcesEvent(SOURCES) + deltaEvent("Provisional text [1]"));
    await screen.findByTestId("answer-cancel");

    fireEvent.click(screen.getByTestId("answer-scope-reset"));
    await waitFor(() => {
      expect(router.state.location.search).toBe("");
    });
    expect(screen.getByTestId("answer-cancel")).toBeDefined();
    expect(stream.stopped).toBe(false);
    expect(posts()).toHaveLength(1);
  });

  it("with the AI off the choice and the chip stay", async () => {
    fakeAnswerServer({ enabled: false, chat_model_configured: true, available: false });
    renderApp("/ask?device=1000");
    await screen.findByTestId("answer-unavailable");
    await listsLoaded();
    expect(choice("answer-device").value).toBe("1000");
    expect(chip()).not.toBeNull();
    expect(askButton().disabled).toBe(true);
  });
});
