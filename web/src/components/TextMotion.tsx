// Text animations of the interface (work order 070, E-52), drawn by classes in
// index.css. While reduced motion is on (settings page or operating system)
// the components render plain text without any animation class.
import { type CSSProperties, Fragment, type ReactElement, type ReactNode } from "react";

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
  level = 2,
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
  level = 2,
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
