// What the answer page shows for a state of the answer (work order 132):
// whether answers can be asked for, the line of the status region, and which
// sources count as evidence. Pure functions, so the rules are tested apart from
// the page.
import type { AnswerSource, AnswerStatus } from "../../api/generated";
import type { AnswerStreamState } from "./useAnswerStream.ts";

/**
 * Whether the form can ask:
 * - "pending": the status is not known yet,
 * - "available": ask,
 * - "off": the AI features are switched off (E-59, D10 (a)),
 * - "unavailable": no chat model is set, or it does not answer.
 */
export type Availability = "pending" | "available" | "off" | "unavailable";

/**
 * Availability from GET /api/v1/answers/status/ and the last answer. A refusal
 * of the stream counts more than the status, which may be up to 15 s old. If
 * the status cannot be read, the form stays usable: the server refuses then.
 */
export function availabilityOf(
  status: AnswerStatus | undefined,
  statusFailed: boolean,
  state: AnswerStreamState,
): Availability {
  if (state.phase === "error") {
    const { failure } = state;
    if (failure.cause === "ai-disabled") {
      return "off";
    }
    if (failure.cause === "http" && failure.code === "chat_not_configured") {
      return "unavailable";
    }
  }
  if (status === undefined) {
    return statusFailed ? "available" : "pending";
  }
  if (!status.enabled) {
    return "off";
  }
  return status.chat_model_configured && status.available ? "available" : "unavailable";
}

/** Key of the short line in the status region (`state.*` in answers.json); null for none. */
export type StatusKey = "searching" | "writing" | "done" | "cancelled";

/** Only changes of state, never every piece of text. */
export function statusKeyOf(state: AnswerStreamState): StatusKey | null {
  switch (state.phase) {
    case "idle":
      return state.cancelled ? "cancelled" : null;
    case "streaming":
      return state.sources === null ? "searching" : "writing";
    case "done":
      return "done";
    case "error":
      // The error itself is announced by its role="alert".
      return null;
  }
}

/**
 * A source is evidence only with a page or a heading path (guard rail 3): a
 * PDF section has its page, a Markdown section its headings. Without either
 * nobody could find the place, so it is never shown as evidence.
 */
export function isEvidence(source: Pick<AnswerSource, "page_start" | "heading_path">): boolean {
  return source.page_start !== null || source.heading_path.some((heading) => heading.trim() !== "");
}

/** The non-empty headings of a source. */
export function headingsOf(source: Pick<AnswerSource, "heading_path">): string[] {
  return source.heading_path.filter((heading) => heading.trim() !== "");
}

/**
 * The sources the checked answer cites, in the order of their numbers. Sources
 * the answer does not cite are left out: they were given to the model but
 * back no statement of the answer.
 */
export function citedSources(sources: readonly AnswerSource[], cited: readonly number[]): AnswerSource[] {
  const numbers = new Set(cited);
  return sources.filter((source) => numbers.has(source.n)).sort((a, b) => a.n - b.n);
}

/**
 * Sources a number in the text may link to: cited by the checked answer, in
 * the list of sources, and evidence. Every other number stays text.
 */
export function citationTargets(sources: readonly AnswerSource[], cited: readonly number[]): Map<number, AnswerSource> {
  return new Map(
    citedSources(sources, cited)
      .filter(isEvidence)
      .map((source) => [source.n, source]),
  );
}
