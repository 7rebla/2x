// Ingestion state of a document version (work order 053): a status badge, the
// translated message of a failed or skipped job with its technical text, and
// the button that starts ingesting again. Reused by the ingest overview (055).
//
// error_detail is technical text from the API (English, data): React renders
// it as text, it never goes through i18next or into HTML.
// With the AI features switched off (E-59) no job ever runs the step "embed";
// missing embeddings are not an error and are not shown.
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type ReactElement, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api/errors.ts";
import type { DocumentVersion, ErrorCodeEnum, IngestJobSummary, IngestStatusEnum } from "../../api/generated";
import { documentVersionIngestMutation } from "../../api/generated/@tanstack/react-query.gen.ts";
import { Icon } from "../../icons/Icon.tsx";
import type { IconName } from "../../icons/names.ts";
import { reloadAfterSave } from "../../pages/structure/save.ts";
import { ErrorMessage } from "../ErrorMessage.tsx";

/** How often a page asks again while a job is queued or running. */
export const INGEST_POLL_INTERVAL_MS = 5000;

/** True while the job is queued or running (no new job can be started then). */
export function isIngestActive(job: IngestJobSummary | null | undefined): boolean {
  return job?.status === "queued" || job?.status === "running";
}

/**
 * refetchInterval of a query that shows these versions: every
 * INGEST_POLL_INTERVAL_MS while one of them has an active job, otherwise no polling.
 */
export function ingestPollInterval(versions: readonly (DocumentVersion | null)[] | undefined): number | false {
  return versions?.some((version) => isIngestActive(version?.ingest)) === true ? INGEST_POLL_INTERVAL_MS : false;
}

/** Kinds of error the web UI has a message for (error codes of work order 042). */
const KNOWN_ERROR_CODES: readonly ErrorCodeEnum[] = [
  "docling_unavailable",
  "docling_rejected",
  "conversion_failed",
  "content_missing",
  "unsupported_format",
  "embedding_unavailable",
  "embedding_rejected",
  "embedding_dimension_mismatch",
  "timeout",
  "internal",
];

function isKnownErrorCode(code: string): code is ErrorCodeEnum {
  return (KNOWN_ERROR_CODES as readonly string[]).includes(code);
}

type BadgeState = IngestStatusEnum | "none";

const BADGE_LOOK: Readonly<Record<BadgeState, { readonly icon: IconName; readonly className: string }>> = {
  queued: { icon: "queued", className: "border-line-strong bg-surface-muted text-fg-muted" },
  running: { icon: "loading", className: "border-info-line bg-info-soft text-info" },
  done: { icon: "success", className: "border-success-line bg-success-soft text-success" },
  failed: { icon: "error", className: "border-danger-line bg-danger-soft text-danger" },
  // Skipping is a known limit (formats until M5), not an error: neutral.
  skipped: { icon: "skipped", className: "border-line-strong bg-surface-muted text-fg-muted" },
  none: { icon: "notIngested", className: "border-line bg-surface text-fg-muted" },
};

/**
 * The state of the newest ingest job of a version as a small badge with icon
 * and text. `compact` leaves out the step and the page and section counts.
 */
export function IngestStatusBadge({
  job,
  compact = false,
}: {
  job: IngestJobSummary | null;
  compact?: boolean;
}): ReactElement {
  const { t } = useTranslation("files");
  const state: BadgeState = job === null ? "none" : job.status;
  const look = BADGE_LOOK[state];

  let text: string = t(`ingest.status.${state}`);
  if (!compact && job !== null && job.status === "running" && job.step !== "") {
    text = t("ingest.runningStep", { step: t(`ingest.step.${job.step}`) });
  }

  const counts: string[] = [];
  if (!compact && job !== null && job.status === "done") {
    if (job.page_count !== null) {
      counts.push(t("ingest.pageCount", { count: job.page_count }));
    }
    if (job.section_count !== null) {
      counts.push(t("ingest.sectionCount", { count: job.section_count }));
    }
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
      <span
        data-testid="ingest-status"
        data-status={state}
        className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${look.className}`}
      >
        <Icon name={look.icon} className={state === "running" ? "animate-spin" : undefined} decorative />
        {text}
      </span>
      {counts.length === 0 ? null : (
        <span data-testid="ingest-counts" className="text-xs text-fg-muted">
          {counts.join(", ")}
        </span>
      )}
    </span>
  );
}

/** The translated message for the kind of error of a job (also for unknown kinds). */
function useErrorMessage(): (code: string) => string {
  const { t } = useTranslation("files");
  return (code) => {
    if (code === "") {
      return t("ingest.error.none");
    }
    return isKnownErrorCode(code) ? t(`ingest.error.${code}`) : t("ingest.error.unknown", { code });
  };
}

/**
 * Why a job failed or was skipped, in words, with the technical text of the
 * API to unfold; for a job that was converted only in part, that hint. Nothing
 * for other jobs.
 */
export function IngestError({ job }: { job: IngestJobSummary | null }): ReactElement | null {
  const { t } = useTranslation("files");
  const errorMessage = useErrorMessage();
  if (job === null) {
    return null;
  }

  let message: string;
  let tone: string;
  if (job.status === "failed") {
    message = errorMessage(job.error_code);
    tone = "text-danger";
  } else if (job.status === "skipped") {
    message = errorMessage(job.error_code);
    tone = "text-fg-muted";
  } else if (job.status === "done" && job.partly_converted) {
    message = t("ingest.partlyConverted");
    tone = "text-warning";
  } else {
    return null;
  }

  return (
    <div data-testid="ingest-error" data-code={job.error_code} className="space-y-1 text-xs">
      <p data-testid="ingest-error-message" className={tone}>
        {job.status === "done" ? <Icon name="warning" className="mr-1" decorative /> : null}
        {message}
      </p>
      {job.error_detail === "" ? null : (
        <details data-testid="ingest-error-details">
          <summary className="cursor-pointer text-fg-muted">{t("ingest.technical")}</summary>
          <p data-testid="ingest-error-detail" className="break-words whitespace-pre-wrap text-fg-muted">
            {job.error_detail}
          </p>
        </details>
      )}
    </div>
  );
}

/**
 * Starts ingesting the version again (role "manage" only; the caller decides
 * who sees it). Hidden while a job is queued or running. A 409 (a job became
 * active meanwhile) and a 400 (configuration) are shown as messages.
 */
export function IngestRetryButton({ version }: { version: DocumentVersion }): ReactElement {
  const { t } = useTranslation("files");
  const queryClient = useQueryClient();
  const mutation = useMutation({
    ...documentVersionIngestMutation(),
    // Success and 409 both change the state of the version: fetch it again.
    onSettled: () => reloadAfterSave(queryClient),
  });
  const { reset } = mutation;
  const active = isIngestActive(version.ingest);

  // An old message ("already being ingested") goes once the active job has ended.
  const wasActive = useRef(active);
  useEffect(() => {
    if (wasActive.current && !active) {
      reset();
    }
    wasActive.current = active;
  }, [active, reset]);

  const error = mutation.error;
  let message: ReactElement | null = null;
  if (error instanceof ApiError && error.kind === "http" && error.status === 409) {
    message = (
      <p role="status" data-testid="ingest-conflict" className="text-xs text-info">
        <Icon name="info" className="mr-1" decorative />
        {t("ingest.active")}
      </p>
    );
  } else if (error instanceof ApiError && error.kind === "http" && error.status === 400) {
    message = (
      <p role="alert" data-testid="ingest-rejected" className="text-xs text-danger">
        <Icon name="error" className="mr-1" decorative />
        {t("ingest.configuration")}
      </p>
    );
  } else if (error !== null) {
    message = <ErrorMessage error={error} />;
  }

  return (
    <div className="space-y-1">
      {active ? null : (
        <button
          type="button"
          data-testid="ingest-retry"
          aria-label={
            version.ingest === null
              ? t("ingest.startVersion", { number: version.number })
              : t("ingest.retryVersion", { number: version.number })
          }
          disabled={mutation.isPending}
          onClick={() => {
            mutation.mutate({ path: { version_id: version.id } });
          }}
          className="inline-flex items-center gap-1 rounded border border-line-strong bg-surface px-2 py-1 text-xs whitespace-nowrap hover:bg-surface-muted disabled:opacity-60"
        >
          <Icon name="retry" decorative />
          {mutation.isPending ? t("ingest.starting") : version.ingest === null ? t("ingest.start") : t("ingest.retry")}
        </button>
      )}
      {message}
    </div>
  );
}
