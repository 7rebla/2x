// Search page (work order 054): form and address, the states of a search,
// hits with pages, heading path, marked snippet, places with links, the
// "older version" mark and the three states of the search by meaning.
import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import enNav from "../locales/en/nav.json";
import { fakeApi, jsonResponse, manager, reader } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";
import { fakeSearchApi, hit, location, sampleResult, SEARCH_PATH } from "./search/testData.ts";

// routes.tsx loads the page lazily; importing it once keeps the first render within the usual waiting time.
beforeAll(async () => {
  await import("./SearchPage.tsx");
});

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

async function hits(): Promise<HTMLElement[]> {
  return screen.findAllByTestId("search-hit");
}

function hitBySection(section: number): HTMLElement {
  const found = screen.getAllByTestId("search-hit").find((item) => item.dataset.section === String(section));
  if (found === undefined) {
    throw new Error(`no hit for section ${String(section)}`);
  }
  return found;
}

describe("form and address", () => {
  it("shows the form and a hint, and sends no search, while the address has no search text", async () => {
    const api = fakeSearchApi();
    fakeApi(reader, api.handler);
    renderApp("/search");

    expect((await screen.findByRole("heading", { level: 1 })).textContent).toBe("Search");
    expect(screen.getByRole("search", { name: "Search the files" })).toBeDefined();
    expect(screen.getByTestId("search-empty").textContent).toBe(
      "Enter a term, an identifier or a question and press Enter.",
    );
    expect(screen.getByLabelText("Search for")).toBeDefined();
    expect(api.searches).toHaveLength(0);
  });

  it("lists the devices grouped by plant, with all devices first", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search");

    const select = await screen.findByLabelText("Device");
    await waitFor(() => {
      expect(within(select).getAllByRole("option")).toHaveLength(5);
    });
    expect(within(select).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "All devices",
      "Test controller (test-plc-1)",
      "Test panel (test-hmi-1)",
      "Test remote I/O (test-io-1)",
      "Test drive (test-drive-1)",
    ]);
    expect(within(select).getAllByRole("group").map((group) => group.getAttribute("label"))).toEqual([
      "Test plant one",
      "Test plant three",
    ]);
  });

  it("searches for the text and the device of the address and fills the form with them", async () => {
    const api = fakeSearchApi();
    fakeApi(reader, api.handler);
    renderApp("/search?q=inspection&device=1003");

    expect(await hits()).toHaveLength(3);
    expect(api.searches).toHaveLength(1);
    expect(api.searches[0]?.get("q")).toBe("inspection");
    expect(api.searches[0]?.getAll("device")).toEqual(["1003"]);
    expect(screen.getByLabelText<HTMLInputElement>("Search for").value).toBe("inspection");
    await waitFor(() => {
      expect(screen.getByLabelText<HTMLSelectElement>("Device").value).toBe("1003");
    });
  });

  it("ignores a device value that cannot be an id and trims the search text", async () => {
    const api = fakeSearchApi();
    fakeApi(reader, api.handler);
    renderApp("/search?q=%20%20inspection%20&device=plc-1");

    await hits();
    expect(api.searches[0]?.get("q")).toBe("inspection");
    expect(api.searches[0]?.has("device")).toBe(false);
  });

  it("names a device of the address that is not in the list by its id", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search?q=inspection&device=4242");

    await hits();
    const select = screen.getByLabelText<HTMLSelectElement>("Device");
    await waitFor(() => {
      expect(select.value).toBe("4242");
    });
    expect(select.selectedOptions[0]?.textContent).toBe("Device no. 4242");
  });

  it("puts the search text and the device into the address when the form is sent (Enter)", async () => {
    const api = fakeSearchApi();
    fakeApi(reader, api.handler);
    const { router } = renderApp("/search");
    const select = await screen.findByLabelText("Device");
    await waitFor(() => {
      expect(within(select).getAllByRole("option")).toHaveLength(5);
    });

    fireEvent.change(screen.getByLabelText("Search for"), { target: { value: "  192.0.2.10 " } });
    fireEvent.change(select, { target: { value: "1000" } });
    // Enter in a text field sends its form: the form has a submit button (implicit submission).
    const form = screen.getByTestId("search-form");
    expect(within(form).getByRole("button", { name: "Search" }).getAttribute("type")).toBe("submit");
    fireEvent.submit(form);

    await hits();
    expect(router.state.location.pathname).toBe("/search");
    const params = new URLSearchParams(router.state.location.search);
    expect(params.get("q")).toBe("192.0.2.10");
    expect(params.get("device")).toBe("1000");
    expect(api.searches.at(-1)?.get("q")).toBe("192.0.2.10");
    expect(api.searches.at(-1)?.getAll("device")).toEqual(["1000"]);
  });

  it("leaves out an empty device and an empty search text", async () => {
    const api = fakeSearchApi();
    fakeApi(reader, api.handler);
    const { router } = renderApp("/search?q=inspection");
    await hits();

    fireEvent.change(screen.getByLabelText("Search for"), { target: { value: "   " } });
    fireEvent.submit(screen.getByTestId("search-form"));

    expect(await screen.findByTestId("search-empty")).toBeDefined();
    expect(router.state.location.search).toBe("");
    expect(api.searches).toHaveLength(1);
  });

  it("goes back to the previous search with Back, with its text in the field", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    const { router } = renderApp("/search?q=first");
    await hits();
    fireEvent.change(screen.getByLabelText("Search for"), { target: { value: "second" } });
    fireEvent.submit(screen.getByTestId("search-form"));
    await waitFor(() => {
      expect(new URLSearchParams(router.state.location.search).get("q")).toBe("second");
    });

    await router.navigate(-1);

    await waitFor(() => {
      expect(screen.getByLabelText<HTMLInputElement>("Search for").value).toBe("first");
    });
  });
});

describe("states", () => {
  it("shows the loading state while the search runs", async () => {
    let answer: (response: Response) => void = () => undefined;
    const pending = new Promise<Response>((resolve) => {
      answer = resolve;
    });
    const base = fakeSearchApi().handler;
    fakeApi(reader, (request) => (new URL(request.url).pathname === SEARCH_PATH ? pending : base(request)));
    renderApp("/search?q=inspection");

    // Before the page itself, the session check and the lazy page show the general loading text.
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("Searching…");
    });
    expect(screen.getByTestId("search-form")).toBeDefined();
    answer(jsonResponse(sampleResult()));
    expect(await hits()).toHaveLength(3);
    expect(screen.queryByTestId("loading")).toBeNull();
  });

  it("says so when there are no hits", async () => {
    fakeApi(reader, fakeSearchApi({ semantic: "used", hits: [] }).handler);
    renderApp("/search?q=nothing");

    expect((await screen.findByTestId("search-no-hits")).textContent).toBe(
      "No hits. Try other words, or search all devices.",
    );
    expect(screen.queryByTestId("search-hit")).toBeNull();
  });

  it("says so in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeSearchApi({ semantic: "used", hits: [] }).handler);
    renderApp("/search?q=nichts");

    expect((await screen.findByTestId("search-no-hits")).textContent).toBe(
      "Keine Treffer. Andere Wörter versuchen oder in allen Geräten suchen.",
    );
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Suche");
  });

  it("shows an error of the API with its status and text", async () => {
    fakeApi(reader, fakeSearchApi(() => jsonResponse({ detail: "Test failure." }, 500)).handler);
    renderApp("/search?q=inspection");

    expect((await screen.findByTestId("error-summary")).textContent).toContain("500");
    expect(screen.getByTestId("error-detail").textContent).toBe("Test failure.");
    expect(screen.queryByTestId("search-results")).toBeNull();
  });

  it("shows a refused search (400) as an error", async () => {
    fakeApi(reader, fakeSearchApi(() => jsonResponse({ q: ["Ensure this field has no more than 500 characters."] }, 400)).handler);
    renderApp("/search?q=inspection");

    expect((await screen.findByTestId("error-summary")).textContent).toContain("400");
  });

  it("shows a missing answer as an error", async () => {
    fakeApi(
      reader,
      fakeSearchApi(() => {
        throw new TypeError("Failed to fetch");
      }).handler,
    );
    renderApp("/search?q=inspection");

    expect(await screen.findByTestId("error-message", {}, { timeout: 5000 })).toBeDefined();
  });
});

describe("search by meaning", () => {
  it("shows the hint only when the language model was not reachable", async () => {
    fakeApi(reader, fakeSearchApi(sampleResult("unavailable")).handler);
    renderApp("/search?q=inspection");

    const hint = await screen.findByTestId("search-semantic-unavailable");
    expect(hint.textContent).toBe("Keyword search only – language model not reachable");
    expect(hint.getAttribute("role")).toBe("status");
    expect(hint.querySelector("svg")?.getAttribute("data-icon")).toBe("warning");
    expect(screen.queryByTestId("search-semantic-disabled")).toBeNull();
    expect(await hits()).toHaveLength(3);
  });

  it("shows the hint in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeSearchApi({ semantic: "unavailable", hits: [] }).handler);
    renderApp("/search?q=nichts");

    expect((await screen.findByTestId("search-semantic-unavailable")).textContent).toBe(
      "Nur Stichwortsuche – Sprachmodell nicht erreichbar",
    );
    expect(screen.getByTestId("search-no-hits")).toBeDefined();
  });

  it("shows a calm line, no hint and no warning, when the AI features are switched off", async () => {
    fakeApi(reader, fakeSearchApi(sampleResult("disabled")).handler);
    renderApp("/search?q=inspection");

    const line = await screen.findByTestId("search-semantic-disabled");
    expect(line.textContent).toBe("Keyword search (AI features not enabled)");
    expect(line.querySelector("svg")).toBeNull();
    expect(line.getAttribute("role")).toBeNull();
    expect(screen.queryByTestId("search-semantic-unavailable")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(await hits()).toHaveLength(3);
  });

  it("says nothing about it when it took part", async () => {
    fakeApi(reader, fakeSearchApi(sampleResult("used")).handler);
    renderApp("/search?q=inspection");

    await hits();
    expect(screen.getByTestId("search-results").dataset.semantic).toBe("used");
    expect(screen.queryByTestId("search-semantic-unavailable")).toBeNull();
    expect(screen.queryByTestId("search-semantic-disabled")).toBeNull();
  });

  it("names how each hit was found", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search?q=inspection");
    await hits();

    const kinds = (section: number): string[] =>
      within(hitBySection(section))
        .getAllByTestId("search-match-kind")
        .map((kind) => kind.textContent);
    expect(kinds(501)).toEqual(["Exact", "Keyword"]);
    expect(kinds(502)).toEqual(["Keyword", "Meaning"]);
    expect(kinds(503)).toEqual(["Meaning"]);
  });

  it("names how each hit was found in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search?q=inspection");
    await hits();

    expect(
      within(hitBySection(501))
        .getAllByTestId("search-match-kind")
        .map((kind) => kind.textContent),
    ).toEqual(["Exakt", "Stichwort"]);
    expect(within(hitBySection(502)).getAllByTestId("search-match-kind")[1]?.textContent).toBe("Bedeutung");
  });
});

describe("hits", () => {
  it("shows the count and the hits in the order of the API", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search?q=inspection");

    expect((await hits()).map((item) => item.dataset.section)).toEqual(["501", "502", "503"]);
    expect(screen.getByTestId("search-count").textContent).toBe("3 hits, best first");
  });

  it("marks the found places in the snippet as <mark>, the rest stays text", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search?q=inspection");
    await hits();

    const snippet = within(hitBySection(501)).getByTestId("search-snippet");
    expect(snippet.textContent).toBe("The inspection of the test station is due every year.");
    expect([...snippet.querySelectorAll("mark")].map((mark) => mark.textContent)).toEqual(["inspection"]);
    const second = within(hitBySection(502)).getByTestId("search-snippet");
    expect([...second.querySelectorAll("mark")].map((mark) => mark.textContent)).toEqual(["192.0.2.10"]);
  });

  it("places the marks by code points, also after an emoji", async () => {
    const snippet = "\u{1F600}\u{1F600} Test \u{1D538} check of the inspection plan";
    // "inspection" starts at code point 23, but at UTF-16 unit 26 (each of the three characters takes two units).
    expect(Array.from(snippet).slice(23, 33).join("")).toBe("inspection");
    expect(snippet.indexOf("inspection")).toBe(26);
    fakeApi(reader, fakeSearchApi({ semantic: "used", hits: [hit(600, { snippet, highlights: [{ start: 23, end: 33 }] })] }).handler);
    renderApp("/search?q=inspection");
    await hits();

    const marks = within(hitBySection(600)).getByTestId("search-snippet").querySelectorAll("mark");
    expect([...marks].map((mark) => mark.textContent)).toEqual(["inspection"]);
  });

  it("renders markup in a snippet as text, never as HTML", async () => {
    const image = '<img src="x" onerror="alert(1)">';
    const snippet = `Test ${image} and <b>bold</b> <script>alert(2)</script>`;
    const highlights = [{ start: 5, end: 5 + image.length }];
    fakeApi(reader, fakeSearchApi({ semantic: "used", hits: [hit(601, { snippet, highlights, heading_path: ["<i>Test</i>"] })] }).handler);
    renderApp("/search?q=img");
    await hits();

    const item = hitBySection(601);
    const shown = within(item).getByTestId("search-snippet");
    expect(shown.textContent).toBe(snippet);
    expect(shown.querySelector("img, b, script")).toBeNull();
    expect(shown.querySelector("mark")?.textContent).toBe(image);
    expect(within(item).getByTestId("search-hit-heading-path").textContent).toBe("Section: <i>Test</i>");
    expect(item.querySelector("i")).toBeNull();
  });

  it("shows one page, a page range, or only the heading path without a page", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search?q=inspection");
    await hits();

    expect(within(hitBySection(501)).getByTestId("search-hit-page").textContent).toBe("p. 31");
    expect(within(hitBySection(502)).getByTestId("search-hit-page").textContent).toBe("pp. 31–32");
    expect(within(hitBySection(503)).queryByTestId("search-hit-page")).toBeNull();
    expect(within(hitBySection(503)).getByTestId("search-hit-heading-path").textContent).toBe(
      "Section: Test notes › Test topic",
    );
    expect(within(hitBySection(501)).getByTestId("search-hit-heading-path").textContent).toBe(
      "Section: Test chapter 3 › Test section 3.2",
    );
  });

  it("shows the pages in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search?q=inspection");
    await hits();

    expect(within(hitBySection(501)).getByTestId("search-hit-page").textContent).toBe("S. 31");
    expect(within(hitBySection(502)).getByTestId("search-hit-page").textContent).toBe("S. 31–32");
  });

  it("shows every place of a hit with file, version, file name, device and plant", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search?q=inspection");
    await hits();

    const places = within(hitBySection(502)).getAllByTestId("search-location");
    expect(places).toHaveLength(2);
    const [first, second] = places as [HTMLElement, HTMLElement];
    expect(within(first).getByTestId("search-location-document").textContent).toBe("Test manual");
    expect(first.textContent).toContain("Version 2");
    expect(within(first).getByTestId("search-location-filename").textContent).toBe("test-manual-v2.pdf");
    expect(within(first).getByTestId("search-location-device").textContent).toBe("Test controller");
    expect(first.textContent).toContain("(test-plc-1)");
    expect(within(first).getByTestId("search-location-plant").textContent).toBe("Plant: Test plant one");
    expect(within(second).getByTestId("search-location-document").textContent).toBe("Test drive notes");
    expect(second.textContent).toContain("Version 1");
    expect(within(second).getByTestId("search-location-filename").textContent).toBe("test-drive-notes.pdf");
    expect(within(second).getByTestId("search-location-device").textContent).toBe("Test drive");
    expect(within(second).getByTestId("search-location-plant").textContent).toBe("Plant: Test plant three");
  });

  it("links each place to the file page and the device page", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search?q=inspection");
    await hits();

    const [first, second] = within(hitBySection(502)).getAllByTestId("search-location") as [HTMLElement, HTMLElement];
    expect(within(first).getByRole("link", { name: "Test manual" }).getAttribute("href")).toBe("/documents/7");
    expect(within(first).getByRole("link", { name: "Test controller" }).getAttribute("href")).toBe("/devices/1000");
    expect(within(second).getByRole("link", { name: "Test drive notes" }).getAttribute("href")).toBe("/documents/8");
    expect(within(second).getByRole("link", { name: "Test drive" }).getAttribute("href")).toBe("/devices/1003");
  });

  it("opens the file page from a hit", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    const { router } = renderApp("/search?q=inspection");
    await hits();

    fireEvent.click(within(hitBySection(501)).getByRole("link", { name: "Test manual" }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/documents/7");
    });
  });

  it("marks only a place in an older version", async () => {
    fakeApi(reader, fakeSearchApi().handler);
    renderApp("/search?q=inspection");
    await hits();

    const [first, second] = within(hitBySection(502)).getAllByTestId("search-location") as [HTMLElement, HTMLElement];
    expect(first.dataset.latest).toBe("true");
    expect(within(first).queryByTestId("search-older-version")).toBeNull();
    expect(second.dataset.latest).toBe("false");
    const older = within(second).getByTestId("search-older-version");
    expect(older.textContent).toBe("Older version");
    expect(older.getAttribute("title")).toBe("This file has a newer version that is not searchable yet.");
    expect(screen.getAllByTestId("search-older-version")).toHaveLength(1);
  });

  it("marks an older version in German", async () => {
    await changeLanguage("de");
    fakeApi(
      reader,
      fakeSearchApi({ semantic: "used", hits: [hit(700, { locations: [location({ isLatest: false })] })] }).handler,
    );
    renderApp("/search?q=Prüfung");
    await hits();

    expect(screen.getByTestId("search-older-version").textContent).toBe("Ältere Version");
  });
});

describe("navigation entry", () => {
  it.each([
    ["reader", reader],
    ["manager", manager],
  ] as const)("is shown to a %s and opens the search page", async (_name, user) => {
    fakeApi(user, fakeSearchApi().handler);
    const { router } = renderApp("/");
    const navigation = await screen.findByRole("navigation", { name: enNav.label });
    const link = await within(navigation).findByRole("link", { name: "Search" });
    expect(link.getAttribute("href")).toBe("/search");
    expect(link.querySelector("svg")?.getAttribute("data-icon")).toBe("search");

    fireEvent.click(link);

    expect(await screen.findByRole("heading", { level: 1, name: "Search" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/search");
    expect(within(navigation).getByRole("link", { name: "Search" }).getAttribute("aria-current")).toBe("page");
    expect(screen.queryByTestId("no-permission")).toBeNull();
  });
});
