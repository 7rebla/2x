import { afterEach, describe, expect, it, vi } from "vitest";

import { installClientConfig } from "../../api/client.ts";
import { ApiError, installApiErrorHandling } from "../../api/errors.ts";
import { sitesCreate } from "../../api/generated";
import { fakeApi, jsonResponse, manager } from "../../test/fakeApi.ts";
import { parseFieldErrors, save } from "./save.ts";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("parseFieldErrors", () => {
  it("reads DRF's messages per field", () => {
    expect(
      parseFieldErrors({
        ip_address: ["Enter a valid IPv4 or IPv6 address."],
        key: ["One.", "Two."],
        non_field_errors: ["Whole entry."],
      }),
    ).toEqual({
      ip_address: ["Enter a valid IPv4 or IPv6 address."],
      key: ["One.", "Two."],
      non_field_errors: ["Whole entry."],
    });
  });

  it("accepts a single text and flattens nested messages", () => {
    expect(parseFieldErrors({ detail: "Bad.", plant: { id: ["Wrong id."] } })).toEqual({
      detail: ["Bad."],
      plant: ["Wrong id."],
    });
  });

  it("drops empty and non-text values", () => {
    expect(parseFieldErrors({ name: [], key: [""], count: 3, flag: null })).toEqual({});
  });

  it.each([null, "text", 42, ["list"]])("gives no field errors for the body %j", (body) => {
    expect(parseFieldErrors(body)).toEqual({});
  });
});

function setUpClient(): void {
  installClientConfig();
  installApiErrorHandling();
}

describe("save", () => {
  it("returns the answer of a successful call", async () => {
    setUpClient();
    fakeApi(manager, () => jsonResponse({ id: 1, name: "Test site" }, 201));

    const outcome = await save(async (fetchFn) => {
      const { data } = await sitesCreate({ body: { name: "Test site" }, fetch: fetchFn, throwOnError: true });
      return data;
    });

    expect(outcome).toEqual({ kind: "saved", data: { id: 1, name: "Test site" } });
  });

  it("reads the field errors of a 400 answer", async () => {
    setUpClient();
    fakeApi(manager, () => jsonResponse({ name: ["A site with this name exists already."] }, 400));

    const outcome = await save((fetchFn) => sitesCreate({ body: { name: "Test site" }, fetch: fetchFn, throwOnError: true }));

    expect(outcome).toEqual({ kind: "invalid", fieldErrors: { name: ["A site with this name exists already."] } });
  });

  it("a 400 answer that is not JSON gives no field errors", async () => {
    setUpClient();
    fakeApi(manager, () => new Response("Bad Request", { status: 400, headers: { "Content-Type": "text/plain" } }));

    const outcome = await save((fetchFn) => sitesCreate({ body: { name: "Test site" }, fetch: fetchFn, throwOnError: true }));

    expect(outcome).toEqual({ kind: "invalid", fieldErrors: {} });
  });

  it("reports other failures with their ApiError", async () => {
    setUpClient();
    fakeApi(manager, () => jsonResponse({ detail: "You do not have permission to perform this action." }, 403));

    const outcome = await save((fetchFn) => sitesCreate({ body: { name: "Test site" }, fetch: fetchFn, throwOnError: true }));

    expect(outcome.kind).toBe("failed");
    const error = outcome.kind === "failed" ? outcome.error : null;
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(403);
  });

  it("a missing answer is a failure, not a field error", async () => {
    setUpClient();
    fakeApi(manager);

    const outcome = await save((fetchFn) => sitesCreate({ body: { name: "Test site" }, fetch: fetchFn, throwOnError: true }));

    expect(outcome.kind).toBe("failed");
    expect(outcome.kind === "failed" && outcome.error instanceof ApiError && outcome.error.kind).toBe("network");
  });
});
