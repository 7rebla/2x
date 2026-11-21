import { describe, expect, it } from "vitest";

import {
  devicePath,
  documentPath,
  downloadPath,
  formatSize,
  limitFromMessage,
  parseId,
  shortChecksum,
  SHORT_CHECKSUM_LENGTH,
} from "./format.ts";

describe("formatSize", () => {
  it.each([
    [0, "en", "0 byte"],
    [999, "en", "999 byte"],
    [1000, "en", "1 kB"],
    [1536, "en", "1.5 kB"],
    [2_500_000, "en", "2.5 MB"],
    [200_000_000, "en", "200 MB"],
    [3_000_000_000, "en", "3 GB"],
    [1536, "de", "1,5 kB"],
    [200_000_000, "de", "200 MB"],
  ])("%d bytes in %s: %s", (bytes, locale, expected) => {
    // Intl separates number and unit with a (narrow) no-break space.
    expect(formatSize(bytes, locale).replace(/\s/gu, " ")).toBe(expected);
  });
});

describe("checksums", () => {
  it("shortens a SHA-256 to its start", () => {
    const sha = "a".repeat(64);
    expect(shortChecksum(sha)).toBe(`${"a".repeat(SHORT_CHECKSUM_LENGTH)}…`);
  });

  it("keeps a value that is already short", () => {
    expect(shortChecksum("abc")).toBe("abc");
  });
});

describe("addresses", () => {
  it("builds the download, file and device addresses", () => {
    expect(downloadPath(71)).toBe("/api/v1/document-versions/71/download/");
    expect(documentPath(7)).toBe("/documents/7");
    expect(devicePath(1000)).toBe("/devices/1000");
  });

  it.each([
    ["1", 1],
    ["42", 42],
    ["9007199254740991", 9007199254740991],
  ])("parseId accepts %s", (raw, id) => {
    expect(parseId(raw)).toBe(id);
  });

  it.each([undefined, "", "0", "07", "-1", "1.5", "abc", "1e3", "9007199254740993"])("parseId rejects %s", (raw) => {
    expect(parseId(raw)).toBeNull();
  });
});

describe("limitFromMessage", () => {
  it.each([
    ["The file is larger than the limit of 200000000 bytes.", 200_000_000],
    ["Die Datei ist größer als die Grenze von 1000 Bytes.", 1000],
    ["No number here.", null],
    [null, null],
    ["limit 0", null],
  ])("%s gives %s", (message, limit) => {
    expect(limitFromMessage(message)).toBe(limit);
  });
});
