// Answer page (address /ask, work order 132): ask a question about the
// ingested documents; the answer streams in and names checked sources.
//
// - The state comes from useAnswerStream (work order 131), whether answers can
//   be asked for from GET /api/v1/answers/status/ (answersStatusQueryOptions).
// - ?q= only fills the field; nothing is ever sent on its own (D14 (i)). The
//   question is not written into the address and nothing is stored (D7).
// - ?device= or ?plant= limits the answers to one device or plant (work order
//   133, answer/scope.ts); the device page links here with ?device=.
// - No jump into the PDF (D14 (f)); sources link to the file page.
// - routes.tsx loads this page on demand with lazyPage(). It has no entry in
//   the navigation yet (work order 134), so it needs the role "read".
import { useQuery } from "@tanstack/react-query";
import { type ReactElement, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";

import { answersStatusQueryOptions } from "../api/answers.ts";
import { AnimatedHeading } from "../components/TextMotion.tsx";
import { usePageTitle } from "../hooks/usePageTitle.ts";
import { AnswerCard } from "./answer/AnswerCard.tsx";
import { AnswerForm } from "./answer/AnswerForm.tsx";
import { AnswerError, AvailabilityNotice, ContradictionNotice, NoEvidence } from "./answer/AnswerStates.tsx";
import { availabilityOf, citationTargets, citedSources, statusKeyOf } from "./answer/answerView.ts";
import { ALL_DEVICES, readScopeAddress, type ScopeAddress, withScopeAddress } from "./answer/scope.ts";
import { ScopeChip } from "./answer/ScopeChip.tsx";
import { SourceList } from "./answer/SourceList.tsx";
import { type AnswerStreamState, useAnswerStream } from "./answer/useAnswerStream.ts";

/** What stands below the form for the state of the answer. */
function AnswerResult({ state, question }: { state: AnswerStreamState; question: string }): ReactElement | null {
  const { t } = useTranslation("answers");
  switch (state.phase) {
    case "idle":
      // A cancelled answer keeps its text, marked as not checked.
      return state.cancelled && state.text !== "" ? (
        <AnswerCard
          text={state.text}
          busy={false}
          label={{ icon: "info", text: t("answer.provisional") }}
          targets={null}
          notes={[t("answer.cancelled")]}
        />
      ) : null;
    case "streaming":
      return state.text === "" ? null : (
        <AnswerCard
          text={state.text}
          busy
          label={{ icon: "info", text: t("answer.provisional") }}
          targets={null}
        />
      );
    case "error":
      return <AnswerError failure={state.failure} />;
    case "done": {
      if (state.status === "no_evidence") {
        // The fixed sentence in the shown language, whatever text the server sent.
        return <NoEvidence question={question} />;
      }
      const sources = citedSources(state.sources ?? [], state.cited);
      const contradiction = state.status === "contradiction";
      return (
        <div className="space-y-4">
          {contradiction ? <ContradictionNotice /> : null}
          <AnswerCard
            text={state.text}
            busy={false}
            label={
              contradiction
                ? { icon: "contradiction", text: t("answer.contradiction") }
                : { icon: "success", text: t("answer.checked") }
            }
            targets={citationTargets(state.sources ?? [], state.cited)}
            notes={state.removedSentences > 0 ? [t("answer.removed")] : []}
          />
          {sources.length === 0 ? null : (
            <section className="space-y-3">
              <h2 className="text-lg font-semibold">{t("sources.label")}</h2>
              <SourceList sources={sources} contradiction={contradiction} />
            </section>
          )}
        </div>
      );
    }
  }
}

/** Questions to the ingested documents (role "read"). */
export function AnswerPage(): ReactElement {
  const { t } = useTranslation("answers");
  usePageTitle(t("title"));
  const [params, setParams] = useSearchParams();
  const initialQuestion = params.get("q") ?? "";
  // The limit to one device or plant stands in the address (work order 133).
  const scope = readScopeAddress(params);
  function changeScope(next: ScopeAddress): void {
    // Replace: choosing does not add history entries; it never sends a question.
    setParams((current) => withScopeAddress(current, next), { replace: true });
  }
  const status = useQuery(answersStatusQueryOptions());
  const { state, ask, cancel } = useAnswerStream();
  /** The question of the shown answer (for the link to the search). */
  const [asked, setAsked] = useState("");

  const availability = availabilityOf(status.data, status.isError, state);
  const locked = availability === "off" || availability === "unavailable";
  const statusKey = statusKeyOf(state);

  return (
    <section className="space-y-4">
      <AnimatedHeading text={t("title")} />
      <p className="max-w-prose text-fg-muted">{t("intro")}</p>
      {locked ? <AvailabilityNotice availability={availability} /> : null}
      {/* Lifting the limit does not stop a running answer; the next question is for all devices. */}
      <ScopeChip
        scope={scope}
        onReset={() => {
          changeScope(ALL_DEVICES);
        }}
      />
      <AnswerForm
        // A new ?q= starts the form again with its text.
        key={initialQuestion}
        initialQuestion={initialQuestion}
        locked={locked}
        waiting={availability === "pending"}
        streaming={state.phase === "streaming"}
        scope={scope}
        onScopeChange={changeScope}
        onAsk={(request) => {
          setAsked(request.question);
          ask(request);
        }}
        onCancel={cancel}
      />
      <p role="status" data-testid="answer-status" className="min-h-5 text-sm text-fg-muted">
        {statusKey === null ? null : t(`state.${statusKey}`)}
      </p>
      <AnswerResult state={state} question={asked} />
    </section>
  );
}
