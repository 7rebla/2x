// Test helper: answer events written for the tests (work order 131). The
// texts are plain test sentences, not taken from any manual; titles, devices
// and plants are invented test names.
import type { AnswerLocation, AnswerSource } from "../../api/generated";
import { sseEvent } from "../../test/fakeApi.ts";

/** A place of a source in the flat form of the stream. */
export function answerLocation(more: Partial<AnswerLocation> = {}): AnswerLocation {
  return {
    section_id: 501,
    document_id: 7,
    document_title: "Test manual",
    version_id: 71,
    version_number: 2,
    version_filename: "test-manual-v2.pdf",
    is_latest_version: true,
    device_id: 1000,
    device_key: "test-plc-1",
    device_name: "Test controller",
    plant_id: 100,
    plant_key: "test-plant-1",
    plant_name: "Test plant one",
    ...more,
  };
}

/** Source number `n` with one place. */
export function answerSource(n: number, more: Partial<AnswerSource> = {}): AnswerSource {
  return {
    n,
    section_id: 500 + n,
    version_id: 71,
    sha256: "0".repeat(64),
    page_start: 3,
    page_end: 4,
    heading_path: ["Maintenance", "Inspection"],
    locations: [answerLocation({ section_id: 500 + n })],
    snippet: `Test sentence of section ${String(n)}.`,
    ...more,
  };
}

export function sourcesEvent(sources: AnswerSource[] = [answerSource(1), answerSource(2)]): string {
  return sseEvent({ type: "sources", sources });
}

export function deltaEvent(text: string): string {
  return sseEvent({ type: "delta", text });
}

export function doneEvent(
  more: { status?: string; cited?: number[]; removed_sentences?: number; final_text?: string } = {},
): string {
  return sseEvent({
    type: "done",
    status: more.status ?? "answered",
    cited: more.cited ?? [1],
    removed_sentences: more.removed_sentences ?? 0,
    final_text: more.final_text ?? "Checked test answer [1].",
  });
}

export function errorEvent(code: string, detail = "Test error text."): string {
  return sseEvent({ type: "error", code, detail });
}
