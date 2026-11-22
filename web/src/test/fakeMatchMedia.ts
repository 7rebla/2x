// Test helper: a fake window.matchMedia (jsdom has none) whose answers the
// test can change; listeners hear the change like in a browser.
import { vi } from "vitest";

export interface FakeMedia {
  /** Sets whether a media query matches and tells its listeners. */
  set: (query: string, matches: boolean) => void;
}

export function fakeMatchMedia(initial: Readonly<Record<string, boolean>> = {}): FakeMedia {
  const state = new Map<string, boolean>(Object.entries(initial));
  const listeners = new Map<string, Set<() => void>>();
  const matchMedia = (query: string): MediaQueryList => {
    const list = {
      media: query,
      get matches(): boolean {
        return state.get(query) ?? false;
      },
      onchange: null,
      addEventListener: (_type: string, listener: () => void): void => {
        const set = listeners.get(query) ?? new Set<() => void>();
        set.add(listener);
        listeners.set(query, set);
      },
      removeEventListener: (_type: string, listener: () => void): void => {
        listeners.get(query)?.delete(listener);
      },
      addListener: (): void => undefined,
      removeListener: (): void => undefined,
      dispatchEvent: (): boolean => true,
    };
    return list as unknown as MediaQueryList;
  };
  vi.stubGlobal("matchMedia", matchMedia);
  return {
    set: (query, matches) => {
      state.set(query, matches);
      for (const listener of listeners.get(query) ?? []) {
        listener();
      }
    },
  };
}
