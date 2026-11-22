// End states of the answer page besides the answer itself (work order 132):
// AI off or not available, no evidence, contradiction, failure. Each carries
// an icon and a text, never colour alone.
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { ErrorMessage } from "../../components/ErrorMessage.tsx";
import { Icon } from "../../icons/Icon.tsx";
import type { Availability } from "./answerView.ts";
import type { AnswerFailure } from "./useAnswerStream.ts";

const LINK_CLASS = "text-accent underline hover:text-accent-strong";

/** Address of the search for `question`; the question enters the address only on this explicit click. */
export function searchPathFor(question: string): string {
  const trimmed = question.trim();
  return trimmed === "" ? "/search" : `/search?${new URLSearchParams({ q: trimmed }).toString()}`;
}

/**
 * Calm hint while answers cannot be asked for (D10 (a), E-59): no warning,
 * like the search page with the AI switched off; the search stays the way.
 */
export function AvailabilityNotice({
  availability,
}: {
  availability: Extract<Availability, "off" | "unavailable">;
}): ReactElement {
  const { t } = useTranslation("answers");
  return (
    <div
      data-testid="answer-unavailable"
      data-availability={availability}
      className="max-w-prose space-y-1 rounded border border-line bg-surface-muted p-3"
    >
      <p className="flex items-start gap-2">
        <Icon name="info" className="mt-1 shrink-0" decorative />
        <span>{availability === "off" ? t("unavailable.off") : t("unavailable.notAvailable")}</span>
      </p>
      <p className="pl-6">
        <Link to="/search" className={LINK_CLASS} data-testid="answer-to-search">
          {t("unavailable.toSearch")}
        </Link>
      </p>
    </div>
  );
}

/** "Nothing on this in the documents": the fixed sentence of the catalog, no sources, a link to the search. */
export function NoEvidence({ question }: { question: string }): ReactElement {
  const { t } = useTranslation("answers");
  return (
    <div
      data-testid="answer-no-evidence"
      className="max-w-prose space-y-2 rounded border border-line bg-surface p-4"
    >
      <p className="flex items-start gap-2 font-semibold">
        <Icon name="noEvidence" size={20} className="shrink-0" decorative />
        <span>{t("noEvidence.text")}</span>
      </p>
      <p className="pl-7 text-sm">
        <Link to={searchPathFor(question)} className={LINK_CLASS} data-testid="answer-search-question">
          {t("noEvidence.search")}
        </Link>
      </p>
    </div>
  );
}

/** Hint above an answer whose sources contradict each other. */
export function ContradictionNotice(): ReactElement {
  const { t } = useTranslation("answers");
  return (
    <p
      data-testid="answer-contradiction"
      className="flex max-w-prose items-start gap-2 rounded border border-warning-line bg-warning-soft p-3 text-warning"
    >
      <Icon name="contradiction" size={20} className="shrink-0" decorative />
      <span>{t("contradiction.text")}</span>
    </p>
  );
}

/** An error of the answer with a fixed text of the catalog. */
function AnswerAlert({ text, code }: { text: string; code?: string }): ReactElement {
  const { t } = useTranslation("answers");
  return (
    <div
      role="alert"
      data-testid="error-message"
      className="max-w-prose space-y-1 rounded border border-danger-line bg-danger-soft p-4 text-danger"
    >
      <p data-testid="error-summary">
        <Icon name="error" className="mr-2" decorative />
        {text}
      </p>
      {code === undefined ? null : (
        <p data-testid="answer-error-code" className="text-sm">
          {t("error.code", { code })}
        </p>
      )}
    </div>
  );
}

/**
 * The failure of an answer. Failures that mean "not available" are shown by
 * AvailabilityNotice instead (null here). The text of an `error` event is not
 * shown: the code has a fixed text, the detail is for the server log.
 */
export function AnswerError({ failure }: { failure: AnswerFailure }): ReactElement | null {
  const { t } = useTranslation("answers");
  switch (failure.cause) {
    case "ai-disabled":
      return null;
    case "interrupted":
      return <AnswerAlert text={t("error.interrupted")} />;
    case "stream":
      return <AnswerAlert text={t(`error.stream.${failure.code}`)} code={failure.code} />;
    case "http":
      if (failure.code === "chat_not_configured") {
        return null;
      }
      if (failure.code === "answer_in_progress") {
        return <AnswerAlert text={t("error.inProgress")} code={failure.code} />;
      }
      if (failure.error.status === 429) {
        return <AnswerAlert text={t("error.tooMany")} />;
      }
      return <ErrorMessage error={failure.error} />;
    case "forbidden":
    case "network":
    case "invalid-answer":
      return <ErrorMessage error={failure.error} />;
  }
}
