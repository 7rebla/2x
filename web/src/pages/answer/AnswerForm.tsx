// The form of the answer page (work order 132): one text area for the
// question, "Ask" and, while an answer streams, "Cancel".
//
// - The button sends; Ctrl+Enter (Cmd+Enter on a Mac) sends as well, Enter
//   alone starts a new line.
// - Nothing is ever sent on its own: ?q= in the address only fills the field
//   (D14 (i)); the question goes into the body of the request, not into the
//   address (D7).
// - The limit to devices or plants (work order 133) goes in here: the form
//   builds the whole request through answerRequest(), the page only passes it on.
import { type KeyboardEvent, type ReactElement, type SubmitEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { AnswerRequest } from "../../api/answers.ts";
import { Button } from "../../components/ui/Button.tsx";
import { Textarea } from "../../components/ui/fields.tsx";

/** Longest question the API accepts (characters after trimming, work order 130). */
export const QUESTION_MAX_LENGTH = 500;

/** Devices and plants an answer is limited to (ids); empty lists: no limit. */
export interface AnswerScope {
  readonly device: readonly number[];
  readonly plant: readonly number[];
}

export const NO_SCOPE: AnswerScope = { device: [], plant: [] };

/** Length as the server counts it: Unicode code points of the trimmed question. */
export function questionLength(question: string): number {
  return Array.from(question.trim()).length;
}

/** The request for `question` within `scope`; empty lists are left out. */
export function answerRequest(question: string, scope: AnswerScope): AnswerRequest {
  const request: AnswerRequest = { question: question.trim() };
  if (scope.device.length > 0) {
    request.device = [...scope.device];
  }
  if (scope.plant.length > 0) {
    request.plant = [...scope.plant];
  }
  return request;
}

export interface AnswerFormProps {
  /** The text of ?q=, or "". */
  readonly initialQuestion: string;
  /** Answers cannot be asked for (AI off or not available): field and button disabled. */
  readonly locked: boolean;
  /** The availability is still being checked: the button waits. */
  readonly waiting: boolean;
  /** An answer streams: "Cancel" shows. */
  readonly streaming: boolean;
  readonly onAsk: (request: AnswerRequest) => void;
  readonly onCancel: () => void;
}

export function AnswerForm({
  initialQuestion,
  locked,
  waiting,
  streaming,
  onAsk,
  onCancel,
}: AnswerFormProps): ReactElement {
  const { t } = useTranslation("answers");
  const [question, setQuestion] = useState(initialQuestion);
  // Work order 133 adds the choice of devices and plants here.
  const scope = NO_SCOPE;
  const questionId = useId();
  const hintId = useId();
  const lengthId = useId();

  const length = questionLength(question);
  const tooLong = length > QUESTION_MAX_LENGTH;
  const canAsk = !locked && !waiting && !streaming && length > 0 && !tooLong;

  function ask(): void {
    if (canAsk) {
      onAsk(answerRequest(question, scope));
    }
  }

  function submit(event: SubmitEvent<HTMLFormElement>): void {
    event.preventDefault();
    ask();
  }

  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      ask();
    }
  }

  return (
    <form aria-label={t("form.label")} data-testid="answer-form" onSubmit={submit} className="max-w-prose space-y-2">
      <div className="flex flex-col gap-1 text-sm">
        <label htmlFor={questionId}>{t("form.question")}</label>
        <Textarea
          id={questionId}
          data-testid="answer-question"
          rows={3}
          value={question}
          disabled={locked}
          invalid={tooLong}
          aria-describedby={`${hintId} ${lengthId}`}
          autoComplete="off"
          className="w-full"
          onChange={(event) => {
            setQuestion(event.target.value);
          }}
          onKeyDown={keyDown}
        />
        <div className="flex flex-wrap justify-between gap-x-3 text-meta text-fg-muted">
          <span id={hintId}>{t("form.hint")}</span>
          <span id={lengthId} data-testid="answer-length" className={tooLong ? "text-danger" : "tabular-nums"}>
            {tooLong
              ? t("form.tooLong", { max: QUESTION_MAX_LENGTH })
              : t("form.length", { length, max: QUESTION_MAX_LENGTH })}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="primary" disabled={!canAsk && !streaming} loading={streaming}>
          {streaming ? t("form.submitting") : t("form.submit")}
        </Button>
        {streaming ? (
          <Button type="button" data-testid="answer-cancel" onClick={onCancel}>
            {t("form.cancel")}
          </Button>
        ) : null}
      </div>
    </form>
  );
}
