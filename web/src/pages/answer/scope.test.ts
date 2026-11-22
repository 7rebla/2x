// The limit of the answer page in the address (work order 133).
import { describe, expect, it } from "vitest";

import { answerRequest, answerScopeOf } from "./AnswerForm.tsx";
import { ALL_DEVICES, chooseDevice, choosePlant, readScopeAddress, withScopeAddress } from "./scope.ts";

describe("readScopeAddress", () => {
  it.each([
    ["", ALL_DEVICES],
    ["device=12", { device: 12, plant: null }],
    ["plant=7", { device: null, plant: 7 }],
    ["device=12&plant=7", { device: 12, plant: null }],
    ["device=abc&plant=7", { device: null, plant: 7 }],
    ["device=0", ALL_DEVICES],
    ["device=-1", ALL_DEVICES],
    ["device=01", ALL_DEVICES],
    ["plant=1e3", ALL_DEVICES],
    ["device=", ALL_DEVICES],
    ["device=12345678901234567", ALL_DEVICES],
  ])("?%s", (search, expected) => {
    expect(readScopeAddress(new URLSearchParams(search))).toEqual(expected);
  });
});

describe("withScopeAddress", () => {
  it("sets one limit, removes the other and keeps ?q=", () => {
    const params = new URLSearchParams("q=Test+question&plant=7");
    expect(withScopeAddress(params, { device: 12, plant: null }).toString()).toBe("q=Test+question&device=12");
    expect(withScopeAddress(params, ALL_DEVICES).toString()).toBe("q=Test+question");
    expect(withScopeAddress(new URLSearchParams(), { device: null, plant: 3 }).toString()).toBe("plant=3");
    // The given parameters stay as they were.
    expect(params.toString()).toBe("q=Test+question&plant=7");
  });

  it("never writes both", () => {
    expect(withScopeAddress(new URLSearchParams(), { device: 1, plant: 2 }).toString()).toBe("device=1");
  });
});

describe("choices", () => {
  it("choosing one resets the other; an empty value means all", () => {
    expect(chooseDevice("12")).toEqual({ device: 12, plant: null });
    expect(choosePlant("7")).toEqual({ device: null, plant: 7 });
    expect(chooseDevice("")).toEqual(ALL_DEVICES);
    expect(choosePlant("")).toEqual(ALL_DEVICES);
  });
});

describe("answerScopeOf", () => {
  it("sends at most one id and no field for all", () => {
    expect(answerRequest(" Test? ", answerScopeOf({ device: 12, plant: null }))).toEqual({
      question: "Test?",
      device: [12],
    });
    expect(answerRequest("Test?", answerScopeOf({ device: null, plant: 7 }))).toEqual({ question: "Test?", plant: [7] });
    expect(answerRequest("Test?", answerScopeOf(ALL_DEVICES))).toEqual({ question: "Test?" });
  });
});
