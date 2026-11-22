// Text animations of the interface (work order 070, E-52; typing: work order
// 076, E-64), drawn by classes in index.css. While reduced motion is on
// (settings page or operating system) the components render plain text
// without any animation class.
import { type CSSProperties, Fragment, type ReactElement, type ReactNode, useEffect, useState } from "react";

import { useReducedMotion } from "../theme/store.ts";

type HeadingLevel = 1 | 2 | 3;

/** Inline style with the position of a word or line (read by index.css as --tx-index). */
function indexStyle(index: number): CSSProperties {
  return { "--tx-index": index } as CSSProperties;
}

function Heading({
  level,
  className,
  testId,
  children,
}: {
  level: HeadingLevel;
  className: string;
  testId: string | undefined;
  children: ReactNode;
}): ReactElement {
  const Tag = `h${String(level)}` as "h1" | "h2" | "h3";
  return (
    <Tag className={className === "" ? undefined : className} data-testid={testId}>
      {children}
    </Tag>
  );
}

/**
 * Pattern A, page headings: the words clear up one after the other when the
 * page opens. Spaces stay text nodes, so the heading reads as before.
 */
export function AnimatedHeading({
  text,
  level = 1,
  className = "text-2xl font-semibold",
  testId,
}: {
  text: string;
  level?: HeadingLevel;
  className?: string;
  testId?: string;
}): ReactElement {
  const reduced = useReducedMotion();
  if (reduced) {
    return (
      <Heading level={level} className={className} testId={testId}>
        {text}
      </Heading>
    );
  }
  const words = text.split(/\s+/).filter((word) => word !== "");
  return (
    <Heading level={level} className={`tx-clear ${className}`.trim()} testId={testId}>
      {words.map((word, index) => (
        // Words of one heading never change order while it is shown; the index is the stable key.
        <Fragment key={`${String(index)}-${word}`}>
          {index > 0 ? " " : null}
          <span className="tx-word" style={indexStyle(index)}>
            {word}
          </span>
        </Fragment>
      ))}
    </Heading>
  );
}

/**
 * Pattern B, page title and device header: the line rises behind a fixed
 * edge. The wrapper keeps its height, so nothing below moves.
 */
export function MaskedTitle({
  text,
  level = 1,
  className = "text-2xl font-semibold",
  testId,
}: {
  text: string;
  level?: HeadingLevel;
  className?: string;
  testId?: string;
}): ReactElement {
  const reduced = useReducedMotion();
  if (reduced) {
    return (
      <Heading level={level} className={className} testId={testId}>
        {text}
      </Heading>
    );
  }
  return (
    <Heading level={level} className={`tx-mask ${className}`.trim()} testId={testId}>
      <span className="tx-line">
        <span style={indexStyle(0)}>{text}</span>
      </span>
    </Heading>
  );
}

const ELLIPSIS = /(…|\.\.\.)$/;

/**
 * Pattern D, loading texts: a band of light runs through the text and the
 * closing ellipsis pulses. The text itself is unchanged.
 */
export function LoadingText({ text }: { text: string }): ReactElement {
  const reduced = useReducedMotion();
  if (reduced) {
    return <span className="text-fg-muted">{text}</span>;
  }
  const match = ELLIPSIS.exec(text);
  const ellipsis = match?.[0] ?? "";
  const body = text.slice(0, text.length - ellipsis.length);
  return (
    <span>
      <span className="tx-sheen">{body}</span>
      {ellipsis === "" ? null : <span className="tx-dots">{ellipsis}</span>}
    </span>
  );
}

/**
 * When the name in the header types itself (pattern E, E-64): once on the
 * sign-in page ("sign-in") and once on the first page after signing in
 * ("app"), each at most once per browser session.
 */
export type TypingRun = "sign-in" | "app";

/** sessionStorage key with the runs this browser session has typed already. */
export const TYPED_STORAGE_KEY = "twox.typed";

/** Runs typed in this browser session; empty without a usable storage. */
export function typedRuns(): TypingRun[] {
  try {
    const raw = window.sessionStorage.getItem(TYPED_STORAGE_KEY) ?? "";
    return raw.split(",").filter((run): run is TypingRun => run === "sign-in" || run === "app");
  } catch {
    return [];
  }
}

/** Remembers that a run has typed; ignored without a usable storage. */
export function markTyped(run: TypingRun): void {
  const runs = typedRuns();
  if (runs.includes(run)) {
    return;
  }
  try {
    window.sessionStorage.setItem(TYPED_STORAGE_KEY, [...runs, run].join(","));
  } catch {
    // Without a storage the name types again on the next page load; nothing else depends on it.
  }
}

/**
 * How the name is shown: "type" types it, "plain" shows it at once, "hidden"
 * keeps its place empty while the session is still loading and the name may
 * type in a moment.
 */
export type TypingMode = "type" | "plain" | "hidden";

function decideTyping(run: TypingRun | "pending"): TypingMode {
  if (run === "pending") {
    return typedRuns().length > 0 ? "plain" : "hidden";
  }
  return typedRuns().includes(run) ? "plain" : "type";
}

/**
 * Decides once per run whether the name types. A run that started typing
 * keeps typing while the component stays on the page, even though the run is
 * then written to the storage.
 */
function useTypingMode(run: TypingRun | "pending"): TypingMode {
  const reduced = useReducedMotion();
  const [decision, setDecision] = useState(() => ({ run, mode: decideTyping(run) }));
  let current = decision;
  if (decision.run !== run) {
    // A new run (session loaded, signed in): decide again while rendering, as React advises for derived state.
    current = { run, mode: decideTyping(run) };
    setDecision(current);
  }
  const typing = current.mode === "type" && current.run !== "pending" ? current.run : null;
  useEffect(() => {
    if (typing !== null) {
      markTyped(typing);
    }
  }, [typing]);
  return reduced ? "plain" : current.mode;
}

/** The characters as a reader sees them (grapheme clusters), so a letter with an accent types as one. */
export function typedCharacters(text: string): string[] {
  // Intl.Segmenter is missing in older browsers (Firefox before 125): fall back to code points.
  if (typeof Intl.Segmenter !== "function") {
    return Array.from(text);
  }
  return Array.from(new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(text), (part) => part.segment);
}

/** Inline style with the position of a typed character (read by index.css as --tx-char). */
function charStyle(index: number): CSSProperties {
  return { "--tx-char": index } as CSSProperties;
}

/**
 * Pattern E, the name in the header types itself like on a console: one
 * character after the other, then a narrow cursor in the brand colour blinks
 * and disappears. The text itself stays a plain text node (the accessible
 * name) and reserves the full width, like the bold copy of .nav-label; the
 * typed layer lies on top of it, is hidden from assistive technology and
 * draws its characters from data-char, so the text of the page stays the name.
 */
export function TypedText({ text, run }: { text: string; run: TypingRun | "pending" }): ReactElement {
  const mode = useTypingMode(run);
  if (mode === "plain") {
    return <span>{text}</span>;
  }
  return (
    <span className="tx-type" data-testid="typed-text" data-typing={mode}>
      <span className="tx-type-text">{text}</span>
      {mode === "type" ? (
        // The key restarts the animation when a new run starts on the same page.
        <span key={run} className="tx-type-layer" aria-hidden="true">
          {typedCharacters(text).map((char, index) => (
            // The characters never change order while the name types; the index is the stable key.
            <span key={`${String(index)}-${char}`} className="tx-type-char" data-char={char} style={charStyle(index)} />
          ))}
        </span>
      ) : null}
    </span>
  );
}
