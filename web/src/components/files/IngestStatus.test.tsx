import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { installClientConfig } from "../../api/client.ts";
import { installApiErrorHandling } from "../../api/errors.ts";
import type { DocumentVersion, ErrorCodeEnum, IngestJobSummary } from "../../api/generated";
import { createQueryClient } from "../../api/queryClient.ts";
import { changeLanguage } from "../../i18n.ts";
import { type FakeApi, fakeApi, jsonResponse, manager } from "../../test/fakeApi.ts";
import {
  INGEST_POLL_INTERVAL_MS,
  IngestError,
  IngestRetryButton,
  IngestStatusBadge,
  ingestPollInterval,
  isIngestActive,
} from "./IngestStatus.tsx";
import { ingestJob, version } from "./testData.ts";

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
});

function renderWithClient(element: ReactElement): void {
  installClientConfig();
  installApiErrorHandling();
  render(<QueryClientProvider client={createQueryClient()}>{element}</QueryClientProvider>);
}

function badge(): HTMLElement {
  return screen.getByTestId("ingest-status");
}

const ERROR_CODES: readonly ErrorCodeEnum[] = [
  "docling_unavailable",
  "docling_rejected",
  "conversion_failed",
  "content_missing",
  "unsupported_format",
  "embedding_unavailable",
  "embedding_rejected",
  "embedding_dimension_mismatch",
  "timeout",
  "internal",
];

describe("IngestStatusBadge", () => {
  it.each([
    ["queued", "Queued", "In Warteschlange"],
    ["running", "Ingesting: converting", "Wird eingelesen: Umwandeln"],
    ["done", "Ingested", "Eingelesen"],
    ["failed", "Error", "Fehler"],
    ["skipped", "Skipped", "Übersprungen"],
  ] as const)("shows the state %s in English and German", async (status, english, german) => {
    const job = ingestJob(status);
    const { rerender } = render(<IngestStatusBadge job={job} />);
    expect(badge().textContent).toBe(english);
    expect(badge().getAttribute("data-status")).toBe(status);
    expect(badge().querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");

    await changeLanguage("de");
    rerender(<IngestStatusBadge job={job} />);
    expect(badge().textContent).toBe(german);
  });

  it("shows a version without any job as not ingested", async () => {
    render(<IngestStatusBadge job={null} />);
    expect(badge().textContent).toBe("Not ingested");
    expect(badge().getAttribute("data-status")).toBe("none");
    await changeLanguage("de");
    cleanup();
    render(<IngestStatusBadge job={null} />);
    expect(badge().textContent).toBe("Nicht eingelesen");
  });

  it.each([
    ["convert", "Ingesting: converting"],
    ["sections", "Ingesting: building sections"],
    ["embed", "Ingesting: computing embeddings"],
    ["", "Ingesting"],
  ] as const)("names the step %j of a running job", (step, text) => {
    render(<IngestStatusBadge job={ingestJob("running", { step })} />);
    expect(badge().textContent).toBe(text);
  });

  it("turns the loading icon only while a job runs", () => {
    render(<IngestStatusBadge job={ingestJob("running")} />);
    expect(badge().querySelector("svg")?.getAttribute("class")).toContain("animate-spin");
    cleanup();
    render(<IngestStatusBadge job={ingestJob("queued")} />);
    expect(badge().querySelector("svg")?.getAttribute("class")).not.toContain("animate-spin");
  });

  it("shows pages and sections of a done job, with plural forms", async () => {
    render(<IngestStatusBadge job={ingestJob("done", { page_count: 12, section_count: 40 })} />);
    expect(screen.getByTestId("ingest-counts").textContent).toBe("12 pages, 40 sections");
    cleanup();
    render(<IngestStatusBadge job={ingestJob("done", { page_count: 1, section_count: 1 })} />);
    expect(screen.getByTestId("ingest-counts").textContent).toBe("1 page, 1 section");
    cleanup();
    await changeLanguage("de");
    render(<IngestStatusBadge job={ingestJob("done", { page_count: 12, section_count: 1 })} />);
    expect(screen.getByTestId("ingest-counts").textContent).toBe("12 Seiten, 1 Abschnitt");
  });

  it("leaves out an unknown page count (e.g. Markdown) and shows no counts for other states", () => {
    render(<IngestStatusBadge job={ingestJob("done", { page_count: null, section_count: 3 })} />);
    expect(screen.getByTestId("ingest-counts").textContent).toBe("3 sections");
    cleanup();
    render(<IngestStatusBadge job={ingestJob("failed")} />);
    expect(screen.queryByTestId("ingest-counts")).toBeNull();
  });

  it("compact shows only the state, without step and counts", () => {
    render(<IngestStatusBadge job={ingestJob("running", { step: "sections" })} compact />);
    expect(badge().textContent).toBe("Ingesting");
    cleanup();
    render(<IngestStatusBadge job={ingestJob("done")} compact />);
    expect(badge().textContent).toBe("Ingested");
    expect(screen.queryByTestId("ingest-counts")).toBeNull();
  });

  it("uses the status colours: success, error, info, and neutral for queued, skipped and none", () => {
    const look = (job: IngestJobSummary | null): string => {
      cleanup();
      render(<IngestStatusBadge job={job} />);
      return badge().className;
    };
    expect(look(ingestJob("done"))).toContain("text-success");
    expect(look(ingestJob("failed"))).toContain("text-danger");
    expect(look(ingestJob("running"))).toContain("text-info");
    for (const job of [ingestJob("queued"), ingestJob("skipped"), null]) {
      const classes = look(job);
      expect(classes).toContain("text-fg-muted");
      expect(classes).not.toMatch(/danger|warning/);
    }
  });
});

describe("IngestError", () => {
  it.each(ERROR_CODES)("has its own English and German message for %s", async (code) => {
    render(<IngestError job={ingestJob("failed", { error_code: code, error_detail: "detail" })} />);
    const english = screen.getByTestId("ingest-error-message").textContent;
    expect(english).not.toContain("ingest.");
    // Not the text for unknown kinds of error.
    expect(english).not.toContain("kind of error");
    cleanup();
    await changeLanguage("de");
    render(<IngestError job={ingestJob("failed", { error_code: code, error_detail: "detail" })} />);
    const german = screen.getByTestId("ingest-error-message").textContent;
    expect(german).not.toBe(english);
    expect(german).not.toContain("ingest.");
  });

  it("gives every kind of error a different message", () => {
    const messages = ERROR_CODES.map((code) => {
      cleanup();
      render(<IngestError job={ingestJob("failed", { error_code: code })} />);
      return screen.getByTestId("ingest-error-message").textContent;
    });
    expect(new Set(messages).size).toBe(ERROR_CODES.length);
  });

  it("explains a skipped format and keeps the technical text folded", () => {
    render(
      <IngestError
        job={ingestJob("skipped", {
          error_code: "unsupported_format",
          error_detail: "unsupported file extension .txt; ingested formats: .pdf, .docx",
        })}
      />,
    );
    expect(screen.getByTestId("ingest-error-message").textContent).toMatch(/^This format is not ingested/);
    expect(screen.getByTestId("ingest-error-message").className).toContain("text-fg-muted");
    const details = screen.getByTestId("ingest-error-details");
    expect(details.tagName).toBe("DETAILS");
    expect(details.hasAttribute("open")).toBe(false);
    expect(screen.getByText("Technical details").tagName).toBe("SUMMARY");
    expect(screen.getByTestId("ingest-error-detail").textContent).toBe(
      "unsupported file extension .txt; ingested formats: .pdf, .docx",
    );
  });

  it("shows a failed job as an error", () => {
    render(<IngestError job={ingestJob("failed", { error_code: "docling_unavailable", error_detail: "x" })} />);
    expect(screen.getByTestId("ingest-error-message").textContent).toBe(
      "The converter (Docling) could not be reached. Please try again later.",
    );
    expect(screen.getByTestId("ingest-error-message").className).toContain("text-danger");
  });

  it("shows an unknown kind of error with a general text and its code as plain text", async () => {
    render(<IngestError job={ingestJob("failed", { error_code: "brand_new" as ErrorCodeEnum })} />);
    expect(screen.getByTestId("ingest-error-message").textContent).toBe(
      "Ingestion did not finish (kind of error: brand_new).",
    );
    cleanup();
    await changeLanguage("de");
    render(<IngestError job={ingestJob("failed", { error_code: "<b>x</b>" as ErrorCodeEnum })} />);
    const message = screen.getByTestId("ingest-error-message");
    expect(message.textContent).toBe("Das Einlesen wurde nicht abgeschlossen (Fehlerart: <b>x</b>).");
    expect(message.querySelector("b")).toBeNull();
  });

  it("shows a failed job without a kind of error with a general text", () => {
    render(<IngestError job={ingestJob("failed")} />);
    expect(screen.getByTestId("ingest-error-message").textContent).toBe("Ingestion did not finish.");
    expect(screen.queryByTestId("ingest-error-details")).toBeNull();
  });

  it("shows error_detail only as text, never as HTML", () => {
    const detail = '<img src="x" onerror="alert(1)"><script>alert(2)</script><b>bold</b>';
    render(<IngestError job={ingestJob("failed", { error_code: "conversion_failed", error_detail: detail })} />);
    const shown = screen.getByTestId("ingest-error-detail");
    expect(shown.textContent).toBe(detail);
    expect(shown.children).toHaveLength(0);
    expect(document.querySelector("img, script, b")).toBeNull();
  });

  it("hints at a partial conversion of a done job", async () => {
    const job = ingestJob("done", {
      partly_converted: true,
      conversion_error_count: 1,
      error_detail: "converted with 1 errors on pages 3",
    });
    render(<IngestError job={job} />);
    const hint = screen.getByTestId("ingest-partly-converted");
    expect(hint.textContent).toBe("Converted only in part: some pages or elements could not be read.");
    expect(hint.className).toContain("text-warning");
    expect(hint.querySelector("svg")?.getAttribute("data-icon")).toBe("warning");
    // A done job has no error message, only the hint.
    expect(screen.queryByTestId("ingest-error-message")).toBeNull();
    expect(screen.getByTestId("ingest-error-detail").textContent).toBe("converted with 1 errors on pages 3");
    cleanup();
    await changeLanguage("de");
    render(<IngestError job={job} />);
    expect(screen.getByTestId("ingest-partly-converted").textContent).toMatch(/^Nur teilweise umgewandelt/);
  });

  it("hints at a partial conversion of an embedding job after a failed embedding", () => {
    // E-62: the embedding job of embed_sections carries the count of the conversion.
    const job = ingestJob("done", {
      step: "embed",
      partly_converted: true,
      conversion_error_count: 2,
      error_detail: "converted with 2 errors",
    });
    render(<IngestError job={job} />);
    expect(screen.getByTestId("ingest-partly-converted").textContent).toBe(
      "Converted only in part: some pages or elements could not be read.",
    );
  });

  it.each(["queued", "running"] as const)(
    "hints at a partial conversion of a %s embedding job",
    async (status) => {
      // The embedding job of a version converted only in part carries the count
      // from its start (E-62), before it has done anything.
      const job = ingestJob(status, {
        step: status === "running" ? "embed" : "",
        partly_converted: true,
        conversion_error_count: 2,
        error_detail: "converted with 2 errors",
      });
      render(<IngestError job={job} />);
      expect(screen.getByTestId("ingest-partly-converted").textContent).toBe(
        "Converted only in part: some pages or elements could not be read.",
      );
      expect(screen.queryByTestId("ingest-error-message")).toBeNull();
      expect(screen.getByTestId("ingest-error-detail").textContent).toBe("converted with 2 errors");
      cleanup();
      await changeLanguage("de");
      render(<IngestError job={job} />);
      expect(screen.getByTestId("ingest-partly-converted").textContent).toBe(
        "Nur teilweise umgewandelt: Einzelne Seiten oder Elemente konnten nicht gelesen werden.",
      );
    },
  );

  it("shows the embedding error of a failed job that was converted only in part", () => {
    const job = ingestJob("failed", {
      step: "embed",
      error_code: "embedding_unavailable",
      error_detail: "cannot reach the model service (gave up after 5 retries)",
      partly_converted: true,
      conversion_error_count: 2,
    });
    render(<IngestError job={job} />);
    expect(screen.getByTestId("ingest-error").dataset.code).toBe("embedding_unavailable");
    const message = screen.getByTestId("ingest-error-message");
    expect(message.className).toContain("text-danger");
    expect(message.textContent).not.toMatch(/Converted only in part/);
    // The hint stands below the error, in its own paragraph and colour (work order 089).
    const hint = screen.getByTestId("ingest-partly-converted");
    expect(hint.textContent).toBe("Converted only in part: some pages or elements could not be read.");
    expect(hint.className).toContain("text-warning");
    expect(message.compareDocumentPosition(hint) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByTestId("ingest-error-detail").textContent).toBe(
      "cannot reach the model service (gave up after 5 retries)",
    );
  });

  it("shows no hint for a failed job that was converted completely", () => {
    render(<IngestError job={ingestJob("failed", { error_code: "conversion_failed" })} />);
    expect(screen.getByTestId("ingest-error-message")).toBeDefined();
    expect(screen.queryByTestId("ingest-partly-converted")).toBeNull();
  });

  it.each(["queued", "running", "done"] as const)("shows nothing for a %s job without a hint", (status) => {
    render(<IngestError job={ingestJob(status)} />);
    expect(screen.queryByTestId("ingest-error")).toBeNull();
  });

  it("shows nothing for a version without a job", () => {
    render(<IngestError job={null} />);
    expect(screen.queryByTestId("ingest-error")).toBeNull();
  });
});

describe("polling rule", () => {
  it("is active only for queued and running jobs", () => {
    expect(isIngestActive(ingestJob("queued"))).toBe(true);
    expect(isIngestActive(ingestJob("running"))).toBe(true);
    for (const status of ["done", "failed", "skipped"] as const) {
      expect(isIngestActive(ingestJob(status))).toBe(false);
    }
    expect(isIngestActive(null)).toBe(false);
    expect(isIngestActive(undefined)).toBe(false);
  });

  it("polls every 5 seconds while one version has an active job, otherwise not", () => {
    expect(INGEST_POLL_INTERVAL_MS).toBe(5000);
    const done = version(1, 1, { ingest: ingestJob("done") });
    const running = version(2, 2, { ingest: ingestJob("running") });
    expect(ingestPollInterval([done, running])).toBe(5000);
    expect(ingestPollInterval([done, null, version(3, 3)])).toBe(false);
    expect(ingestPollInterval([])).toBe(false);
    expect(ingestPollInterval(undefined)).toBe(false);
  });
});

describe("IngestRetryButton", () => {
  const INGEST_PATH = "/api/v1/document-versions/70/ingest/";

  function serveIngest(answer: () => Response): FakeApi {
    return fakeApi(manager, (request) =>
      new URL(request.url).pathname === INGEST_PATH && request.method === "POST"
        ? answer()
        : jsonResponse({ detail: "Not found." }, 404),
    );
  }

  function failedVersion(): DocumentVersion {
    return version(70, 1, { ingest: ingestJob("failed", { error_code: "docling_unavailable" }) });
  }

  it("starts ingesting the version again with a POST to its ingest endpoint", async () => {
    const api = serveIngest(() => jsonResponse({ ...ingestJob("queued"), requested_by: "test-manager" }, 202));
    renderWithClient(<IngestRetryButton version={failedVersion()} />);

    const button = screen.getByRole("button", { name: "Ingest version 1 again" });
    expect(button.textContent).toBe("Ingest again");
    fireEvent.click(button);

    await waitFor(() => {
      expect(api.requestsTo(INGEST_PATH)).toHaveLength(1);
    });
    const request = api.requestsTo(INGEST_PATH)[0];
    expect(request?.method).toBe("POST");
    expect(screen.queryByTestId("ingest-conflict")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("is called Ingest for a version that was never ingested", async () => {
    renderWithClient(<IngestRetryButton version={version(70, 1)} />);
    expect(screen.getByTestId("ingest-retry").textContent).toBe("Ingest");
    await changeLanguage("de");
    cleanup();
    renderWithClient(<IngestRetryButton version={version(70, 1)} />);
    expect(screen.getByRole("button", { name: "Version 1 einlesen" }).textContent).toBe("Einlesen");
  });

  it.each(["queued", "running"] as const)("is hidden while a job is %s", (status) => {
    renderWithClient(<IngestRetryButton version={version(70, 1, { ingest: ingestJob(status) })} />);
    expect(screen.queryByTestId("ingest-retry")).toBeNull();
  });

  it.each(["done", "failed", "skipped"] as const)("is shown after a %s job", (status) => {
    renderWithClient(<IngestRetryButton version={version(70, 1, { ingest: ingestJob(status) })} />);
    expect(screen.getByTestId("ingest-retry").textContent).toBe("Ingest again");
  });

  it("shows a 409 as the message that the version is being ingested already", async () => {
    serveIngest(() =>
      jsonResponse(
        { detail: "This document version is being ingested already.", code: "ingest_active", job: ingestJob("running") },
        409,
      ),
    );
    renderWithClient(<IngestRetryButton version={failedVersion()} />);
    fireEvent.click(screen.getByTestId("ingest-retry"));

    expect((await screen.findByTestId("ingest-conflict")).textContent).toBe("This version is already being ingested.");
    expect(screen.queryByTestId("error-message")).toBeNull();
  });

  it("shows the 409 message in German", async () => {
    await changeLanguage("de");
    serveIngest(() => jsonResponse({ detail: "x", code: "ingest_active", job: ingestJob("queued") }, 409));
    renderWithClient(<IngestRetryButton version={failedVersion()} />);
    fireEvent.click(screen.getByRole("button", { name: "Version 1 erneut einlesen" }));

    expect((await screen.findByTestId("ingest-conflict")).textContent).toBe("Diese Version wird bereits eingelesen.");
  });

  it("shows a 400 for a configuration as its own message", async () => {
    serveIngest(() => jsonResponse({ detail: "x", code: "configuration_not_ingested" }, 400));
    renderWithClient(<IngestRetryButton version={failedVersion()} />);
    fireEvent.click(screen.getByTestId("ingest-retry"));

    expect((await screen.findByTestId("ingest-rejected")).textContent).toBe("Configuration files are not ingested.");
  });

  it("shows other errors with the shared error message", async () => {
    serveIngest(() => jsonResponse({ detail: "Server trouble." }, 500));
    renderWithClient(<IngestRetryButton version={failedVersion()} />);
    fireEvent.click(screen.getByTestId("ingest-retry"));

    expect((await screen.findByTestId("error-summary")).textContent).toBe("The API answered with HTTP status 500.");
  });
});
