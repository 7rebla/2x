// The form of the answer page (work order 132): one text area for the
// question, "Ask" and, while an answer streams, "Cancel".
//
// - The button sends; Ctrl+Enter (Cmd+Enter on a Mac) sends as well, Enter
//   alone starts a new line.
// - Nothing is ever sent on its own: ?q= in the address only fills the field
//   (D14 (i)); the question goes into the body of the request, not into the
//   address (D7).
// - The limit to one device or one plant (work order 133): two choices below
//   the question. The limit lives in the address (scope.ts); the form shows it
//   and reports a change through onScopeChange, which sends nothing. The form
//   builds the whole request through answerRequest(), the page only passes it on.
import { useQuery } from "@tanstack/react-query";
import { type KeyboardEvent, type ReactElement, type SubmitEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { AnswerRequest } from "../../api/answers.ts";
import { devicesListOptions, plantsListOptions } from "../../api/generated/@tanstack/react-query.gen.ts";
import { devicesByPlant } from "../../components/devicesByPlant.ts";
import { ErrorMessage } from "../../components/ErrorMessage.tsx";
import { Button } from "../../components/ui/Button.tsx";
import { Select, Textarea } from "../../components/ui/fields.tsx";
import { chooseDevice, choosePlant, type ScopeAddress } from "./scope.ts";

/** Longest question the API accepts (characters after trimming, work order 130). */
export const QUESTION_MAX_LENGTH = 500;

/** Devices and plants an answer is limited to (ids); empty lists: no limit. */
export interface AnswerScope {
  readonly device: readonly number[];
  readonly plant: readonly number[];
}

export const NO_SCOPE: AnswerScope = { device: [], plant: [] };

/** The scope of a request for the limit in the address: at most one id, none for "all". */
export function answerScopeOf(address: ScopeAddress): AnswerScope {
  return {
    device: address.device === null ? [] : [address.device],
    plant: address.plant === null ? [] : [address.plant],
  };
}

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
  /** The limit from the address (work order 133). */
  readonly scope: ScopeAddress;
  /** A new limit was chosen: write it into the address; nothing is sent. */
  readonly onScopeChange: (scope: ScopeAddress) => void;
  readonly onAsk: (request: AnswerRequest) => void;
  readonly onCancel: () => void;
}

/**
 * The choice of one device or one plant. Both stay usable while the AI is
 * off or an answer streams: a change only applies to the next question.
 */
function ScopeChoice({
  scope,
  onScopeChange,
}: {
  scope: ScopeAddress;
  onScopeChange: (scope: ScopeAddress) => void;
}): ReactElement {
  const { t } = useTranslation("answers");
  const devices = useQuery(devicesListOptions());
  const plants = useQuery(plantsListOptions());
  const deviceId = useId();
  const plantId = useId();

  const knownDevices = devices.data ?? [];
  const knownPlants = [...(plants.data ?? [])].sort(
    (a, b) => a.name.localeCompare(b.name) || a.key.localeCompare(b.key),
  );
  // An id from the address that the lists do not have stays visible as its own entry.
  const unknownDevice =
    scope.device !== null && devices.isSuccess && !knownDevices.some((item) => item.id === scope.device)
      ? scope.device
      : null;
  const unknownPlant =
    scope.plant !== null && plants.isSuccess && !knownPlants.some((item) => item.id === scope.plant)
      ? scope.plant
      : null;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex min-w-0 flex-col gap-1 text-sm">
          <label htmlFor={deviceId}>{t("scope.device")}</label>
          <Select
            id={deviceId}
            data-testid="answer-device"
            className="w-full max-w-72"
            value={scope.device === null ? "" : String(scope.device)}
            aria-busy={devices.isPending}
            onChange={(event) => {
              onScopeChange(chooseDevice(event.target.value));
            }}
          >
            <option value="">{t("scope.allDevices")}</option>
            {unknownDevice === null ? null : (
              <option value={String(unknownDevice)}>{t("scope.unknownDevice", { id: unknownDevice })}</option>
            )}
            {devicesByPlant(knownDevices).map((group) => (
              <optgroup key={group.plantId} label={group.plantName}>
                {group.devices.map((item) => (
                  <option key={item.id} value={String(item.id)}>
                    {`${item.name} (${item.key})`}
                  </option>
                ))}
              </optgroup>
            ))}
          </Select>
        </div>
        <div className="flex min-w-0 flex-col gap-1 text-sm">
          <label htmlFor={plantId}>{t("scope.plant")}</label>
          <Select
            id={plantId}
            data-testid="answer-plant"
            className="w-full max-w-72"
            value={scope.plant === null ? "" : String(scope.plant)}
            aria-busy={plants.isPending}
            onChange={(event) => {
              onScopeChange(choosePlant(event.target.value));
            }}
          >
            <option value="">{t("scope.allPlants")}</option>
            {unknownPlant === null ? null : (
              <option value={String(unknownPlant)}>{t("scope.unknownPlant", { id: unknownPlant })}</option>
            )}
            {knownPlants.map((item) => (
              <option key={item.id} value={String(item.id)}>
                {`${item.name} (${item.key})`}
              </option>
            ))}
          </Select>
        </div>
      </div>
      {devices.isError ? <ErrorMessage error={devices.error} /> : null}
      {plants.isError && !devices.isError ? <ErrorMessage error={plants.error} /> : null}
    </div>
  );
}

export function AnswerForm({
  initialQuestion,
  locked,
  waiting,
  streaming,
  scope: address,
  onScopeChange,
  onAsk,
  onCancel,
}: AnswerFormProps): ReactElement {
  const { t } = useTranslation("answers");
  const [question, setQuestion] = useState(initialQuestion);
  const scope = answerScopeOf(address);
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
      <ScopeChoice scope={address} onScopeChange={onScopeChange} />
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
