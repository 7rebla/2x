// Ingest overview (address /ingest, work order 055): the ingest jobs of all
// devices, newest first, 50 per page like /audit. Without a filter the page
// lists what needs attention: failed, running and queued jobs. "All" adds the
// ingested and the skipped ones.
//
// Status, device and the switch for older attempts stand in the browser
// address (/ingest?status=…&device=…&older=1), so a view can be linked,
// reloaded and reached with Back. While a listed job is queued or running,
// the page asks again every 5 seconds; otherwise it does not poll.
//
// Every job is one attempt (E-55). By default the page lists only the newest
// job of each version (latest=true, work order 064), so a failed attempt that
// a later one has ingested is not "open" any more. The switch "Also show older
// attempts" lists every attempt; a row that is not the newest job of its
// version (is_latest false) says so and has no button.
//
// Device names, file titles, file names and error_detail are data: React
// renders them as text, they never go through the interpolation of i18next.
// The badge, the error message and the button come from
// components/files/IngestStatus.tsx (work order 053). routes.tsx loads this
// page with lazy().
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { type ReactElement, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";

import type { Device, IngestJob, IngestJobsListData, IngestStatusEnum } from "../api/generated";
import { devicesListOptions, ingestJobsListOptions } from "../api/generated/@tanstack/react-query.gen.ts";
import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { devicePath, documentPath, parseId } from "../components/files/format.ts";
import {
  INGEST_POLL_INTERVAL_MS,
  IngestError,
  IngestRetryButton,
  IngestStatusBadge,
  isIngestActive,
} from "../components/files/IngestStatus.tsx";
import { DateTime } from "../components/files/parts.tsx";
import { Loading } from "../components/Loading.tsx";
import { type CountReport, ResultCount, useReportCount, useResultCount } from "../components/ResultCount.tsx";
import { AnimatedHeading } from "../components/TextMotion.tsx";
import { usePageTitle } from "../hooks/usePageTitle.ts";
import { Button } from "../components/ui/Button.tsx";
import { Select } from "../components/ui/fields.tsx";
import { ResponsiveTable, type TableColumn } from "../components/ui/ResponsiveTable.tsx";
import { Icon } from "../icons/Icon.tsx";
import { useRole } from "../session.ts";

/** Jobs per page; fixed by the API (work order 051). */
export const INGEST_PAGE_SIZE = 50;

/** The states of an ingest job, in the order of the status choice. */
export const ingestStatuses = ["failed", "running", "queued", "done", "skipped"] as const satisfies readonly IngestStatusEnum[];

/** The states the page lists without a filter: what needs attention. */
export const OPEN_STATUSES: readonly IngestStatusEnum[] = ["failed", "running", "queued"];

/** Choice of the status filter: the open jobs (default), one state, or all jobs. */
export type StatusFilter = "open" | "all" | IngestStatusEnum;

const STATUS_FILTERS: readonly StatusFilter[] = ["open", ...ingestStatuses, "all"];

/** What the address asks for. */
export interface IngestAddress {
  readonly status: StatusFilter;
  /** Id of the device, null for all devices. */
  readonly device: number | null;
  /** Also list older attempts; false (the default) lists only the newest job of each version. */
  readonly older: boolean;
}

/** Value of ?older= that switches older attempts on. */
const OLDER_ON = "1";

function isStatusFilter(value: string): value is StatusFilter {
  return (STATUS_FILTERS as readonly string[]).includes(value);
}

/**
 * Reads ?status=, ?device= and ?older= from the address. A missing or unknown
 * status means the open jobs; a device value that cannot be an id means all
 * devices; older attempts show only with ?older=1.
 */
export function readIngestAddress(params: URLSearchParams): IngestAddress {
  const status = params.get("status") ?? "";
  return {
    status: isStatusFilter(status) ? status : "open",
    device: parseId(params.get("device") ?? undefined),
    older: params.get("older") === OLDER_ON,
  };
}

/** The address parameters of a view; the defaults (open jobs, all devices, newest jobs only) are left out. */
export function ingestAddressParams({ status, device, older }: IngestAddress): URLSearchParams {
  const params = new URLSearchParams();
  if (status !== "open") {
    params.set("status", status);
  }
  if (device !== null) {
    params.set("device", String(device));
  }
  if (older) {
    params.set("older", OLDER_ON);
  }
  return params;
}

/** The states sent to the API for a status choice; none (no filter) for "all". */
export function statusesFor(filter: StatusFilter): IngestStatusEnum[] | undefined {
  if (filter === "all") {
    return undefined;
  }
  return filter === "open" ? [...OPEN_STATUSES] : [filter];
}

function queryFor(address: IngestAddress, page: number): NonNullable<IngestJobsListData["query"]> {
  const query: NonNullable<IngestJobsListData["query"]> = {};
  if (!address.older) {
    query.latest = true;
  }
  const statuses = statusesFor(address.status);
  if (statuses !== undefined) {
    query.status = statuses;
  }
  if (address.device !== null) {
    query.device = address.device;
  }
  if (page > 1) {
    query.page = page;
  }
  return query;
}

/** Devices grouped by plant, plants and devices by name, for the device choice. */
function devicesByPlant(devices: readonly Device[]): { plantId: number; plantName: string; devices: Device[] }[] {
  const sorted = [...devices].sort(
    (a, b) =>
      a.plant.name.localeCompare(b.plant.name) || a.name.localeCompare(b.name) || a.key.localeCompare(b.key),
  );
  const groups: { plantId: number; plantName: string; devices: Device[] }[] = [];
  for (const device of sorted) {
    const last = groups.at(-1);
    if (last?.plantId === device.plant.id) {
      last.devices.push(device);
    } else {
      groups.push({ plantId: device.plant.id, plantName: device.plant.name, devices: [device] });
    }
  }
  return groups;
}

/** The two choices; a change applies at once and goes into the address. */
function IngestFilter({
  address,
  onChange,
}: {
  address: IngestAddress;
  onChange: (address: IngestAddress) => void;
}): ReactElement {
  const { t } = useTranslation("ingest");
  const devices = useQuery(devicesListOptions());
  const statusId = useId();
  const deviceId = useId();
  const known = devices.data ?? [];
  const chosenUnknown = address.device !== null && devices.isSuccess && !known.some((item) => item.id === address.device);

  return (
    <form
      data-testid="ingest-filter"
      onSubmit={(event) => {
        event.preventDefault();
      }}
      className="space-y-2"
    >
      <fieldset className="flex min-w-0 flex-wrap items-end gap-3">
        <legend className="sr-only">{t("filter.legend")}</legend>
        <div className="flex max-w-full min-w-0 flex-col gap-1 text-sm">
          <label htmlFor={statusId}>{t("filter.status")}</label>
          <Select
            id={statusId}
            data-testid="ingest-filter-status"
            className="max-w-full"
            value={address.status}
            onChange={(event) => {
              const value = event.target.value;
              onChange({ ...address, status: isStatusFilter(value) ? value : "open" });
            }}
          >
            {STATUS_FILTERS.map((filter) => (
              <option key={filter} value={filter}>
                {t(`statusFilter.${filter}`)}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex max-w-full min-w-0 flex-col gap-1 text-sm">
          <label htmlFor={deviceId}>{t("filter.device")}</label>
          <Select
            id={deviceId}
            data-testid="ingest-filter-device"
            className="max-w-full sm:max-w-72"
            value={address.device === null ? "" : String(address.device)}
            aria-busy={devices.isPending}
            onChange={(event) => {
              const value = event.target.value;
              onChange({ ...address, device: parseId(value === "" ? undefined : value) });
            }}
          >
            <option value="">{t("filter.allDevices")}</option>
            {chosenUnknown ? (
              <option value={String(address.device)}>{t("filter.unknownDevice", { id: address.device })}</option>
            ) : null}
            {devicesByPlant(known).map((group) => (
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
        {/* As high as the choices (36 px), so the check box sits on their middle line. */}
        <label className="flex min-h-9 max-w-full min-w-0 items-center gap-2 text-sm">
          <input
            type="checkbox"
            data-testid="ingest-filter-older"
            className="size-4 shrink-0 accent-accent"
            checked={address.older}
            onChange={(event) => {
              onChange({ ...address, older: event.target.checked });
            }}
          />
          {t("filter.older")}
        </label>
      </fieldset>
      {devices.isError ? <ErrorMessage error={devices.error} /> : null}
    </form>
  );
}

/** One page of jobs at a time, with "previous" and "next"; a new filter starts on page 1 (key in IngestPage). */
function IngestJobs({
  address,
  filterKey,
  reportCount,
}: {
  address: IngestAddress;
  filterKey: string;
  reportCount: (report: CountReport) => void;
}): ReactElement {
  const { t } = useTranslation("ingest");
  const { canManage } = useRole();
  const [page, setPage] = useState(1);
  const query = useQuery({
    ...ingestJobsListOptions({ query: queryFor(address, page) }),
    // Keep the shown page while the next one loads, so the table does not jump.
    placeholderData: keepPreviousData,
    // Poll only while a listed job is queued or running.
    refetchInterval: (current) =>
      current.state.data?.results.some((job) => isIngestActive(job)) === true ? INGEST_POLL_INTERVAL_MS : false,
  });
  // The number of jobs goes to the live region of the page; polling with an
  // unchanged number changes nothing there.
  useReportCount(filterKey, query.data?.count, reportCount);
  // The page whose jobs are shown: while the next page loads, the table still shows the previous one.
  const [shownPage, setShownPage] = useState(page);
  if (query.isSuccess && !query.isPlaceholderData && shownPage !== page) {
    setShownPage(page);
  }

  if (query.data === undefined) {
    return query.isError ? <ErrorMessage error={query.error} /> : <Loading />;
  }

  const { count, results, next } = query.data;
  const pages = Math.max(1, Math.ceil(count / INGEST_PAGE_SIZE));
  const busy = query.isPlaceholderData;
  const polling = results.some((job) => isIngestActive(job));

  return (
    <div data-testid="ingest-jobs" className="space-y-3" aria-busy={busy}>
      {/* A failed reload keeps the last list on screen and says so. */}
      {query.error === null ? null : <ErrorMessage error={query.error} />}
      {polling ? (
        <p data-testid="ingest-polling" className="text-sm text-fg-muted">
          {t("polling")}
        </p>
      ) : null}
      {/* No jobs: the result count above says so. */}
      {results.length === 0 ? null : <IngestJobTable jobs={results} canManage={canManage} />}
      <nav aria-label={t("pagination.label")} className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          icon="previous"
          data-testid="ingest-previous"
          disabled={busy || shownPage <= 1}
          onClick={() => {
            setPage(shownPage - 1);
          }}
        >
          {t("pagination.previous")}
        </Button>
        <span data-testid="ingest-page-status">{t("pagination.status", { page: shownPage, pages })}</span>
        <Button
          type="button"
          icon="next"
          iconPosition="end"
          data-testid="ingest-next"
          disabled={busy || next === null || next === undefined}
          onClick={() => {
            setPage(shownPage + 1);
          }}
        >
          {t("pagination.next")}
        </Button>
      </nav>
    </div>
  );
}

/**
 * The jobs as a table from 768 px; below that every job is a card (work order
 * 081): the file as heading, the state below it, then device, version, times
 * and (managers) who started it.
 */
function IngestJobTable({ jobs, canManage }: { jobs: readonly IngestJob[]; canManage: boolean }): ReactElement {
  const { t } = useTranslation("ingest");
  const columns: TableColumn<IngestJob>[] = [
    {
      key: "device",
      header: t("column.device"),
      headerClassName: "p-2 font-semibold",
      className: "p-2",
      testId: "ingest-job-device",
      cell: (job) => (
        <>
          <Link to={devicePath(job.device.id)} className="text-accent underline hover:text-accent-strong">
            <Icon name="device" className="mr-1" decorative />
            {job.device.name}
          </Link>
          <span className="block text-meta text-fg-muted tabular-nums slashed-zero">{job.device.key}</span>
        </>
      ),
    },
    {
      key: "document",
      header: t("column.document"),
      headerClassName: "p-2 font-semibold",
      className: "p-2",
      testId: "ingest-job-document",
      card: "title",
      cell: (job) => (
        <>
          <DocumentLink job={job} />
          <VersionLine job={job} />
        </>
      ),
      cardCell: (job) => <DocumentLink job={job} />,
    },
    {
      key: "status",
      header: t("column.status"),
      headerClassName: "p-2 font-semibold",
      className: "min-w-56 space-y-1 p-2",
      testId: "ingest-job-status",
      card: "status",
      cell: (job) => <JobState job={job} canManage={canManage} />,
    },
    {
      // In the table the version stands below the file title; on a card as a pair.
      key: "version",
      header: t("column.version"),
      table: false,
      cell: (job) => <VersionLine job={job} />,
    },
    {
      key: "times",
      header: t("column.times"),
      headerClassName: "p-2 font-semibold",
      className: "p-2 text-meta whitespace-nowrap tabular-nums",
      testId: "ingest-job-times",
      cell: (job) => (
        <>
          <span className="block">
            <span className="text-fg-muted">{t("created")}: </span>
            <DateTime iso={job.created_at} />
          </span>
          <span className="block">
            <span className="text-fg-muted">{t("finished")}: </span>
            {job.finished_at === null ? t("notFinished") : <DateTime iso={job.finished_at} />}
          </span>
        </>
      ),
    },
  ];
  if (canManage) {
    columns.push({
      key: "requestedBy",
      header: t("column.requestedBy"),
      headerClassName: "p-2 font-semibold whitespace-nowrap",
      headerTestId: "ingest-column-requested-by",
      className: "p-2 whitespace-nowrap",
      testId: "ingest-job-requested-by",
      cell: (job) => job.requested_by ?? <span className="text-fg-muted">{t("system")}</span>,
    });
  }
  return (
    <ResponsiveTable
      label={t("tableLabel")}
      rows={jobs}
      rowKey={(job) => job.id}
      columns={columns}
      rowAttributes={(job) => ({ "data-testid": "ingest-job", "data-job": job.id, "data-status": job.status })}
      cardHeadingLevel={2}
      tableClassName="border-collapse"
      headerRowClassName="border-b border-line"
      rowClassName="border-b border-line align-top"
    />
  );
}

function DocumentLink({ job }: { job: IngestJob }): ReactElement {
  return (
    <Link
      to={documentPath(job.document.id)}
      data-testid="ingest-job-document-link"
      className="break-words text-accent underline hover:text-accent-strong"
    >
      <Icon name="document" className="mr-1" decorative />
      {job.document.title}
    </Link>
  );
}

/** "Version N · file name"; the name wraps at word boundaries and is cut after two lines, the tooltip has all of it (079). */
function VersionLine({ job }: { job: IngestJob }): ReactElement {
  const { t } = useTranslation("ingest");
  return (
    <span
      className="line-clamp-2 max-w-xs text-meta break-words text-fg-muted"
      title={job.version.original_filename}
      data-testid="ingest-job-version"
    >
      <span className="whitespace-nowrap">{t("version", { number: job.version.number })}</span>
      {" · "}
      {job.version.original_filename}
    </span>
  );
}

function JobState({ job, canManage }: { job: IngestJob; canManage: boolean }): ReactElement {
  const { t } = useTranslation("ingest");
  // The API says whether a newer job of the same version exists, on any page.
  const superseded = !job.is_latest;
  return (
    <>
      <IngestStatusBadge job={job} />
      <IngestError job={job} />
      {superseded ? (
        <p data-testid="ingest-superseded" className="text-meta text-fg-muted">
          {t("superseded")}
        </p>
      ) : canManage ? (
        <IngestRetryButton version={{ id: job.version.id, number: job.version.number, ingest: job }} />
      ) : null}
    </>
  );
}

/** The ingest overview (role "read"; the button to ingest again only for "manage"). */
export function IngestPage(): ReactElement {
  const { t } = useTranslation(["nav", "ingest"]);
  usePageTitle(t("nav:ingest"));
  const [params, setParams] = useSearchParams();
  const address = readIngestAddress(params);
  // A new filter (a choice, Back, a link) starts again on page 1.
  const filterKey = ingestAddressParams(address).toString();
  // The number of jobs stays outside IngestJobs, which a new filter mounts
  // afresh: the live region remains and announces the new number (work order 089).
  const [count, reportCount] = useResultCount(filterKey);

  return (
    <section className="space-y-4">
      <AnimatedHeading text={t("nav:ingest")} />
      <p className="text-fg-muted">{t("ingest:intro")}</p>
      <IngestFilter
        address={address}
        onChange={(next) => {
          setParams(ingestAddressParams(next));
        }}
      />
      <ResultCount
        count={count}
        text={(jobs) => t("ingest:resultCount", { count: jobs })}
        empty={address.status === "open" && address.device === null ? t("ingest:empty.open") : t("ingest:empty.filtered")}
        testId="ingest-result-count"
        countTestId="ingest-total"
        emptyTestId="ingest-empty"
      />
      <IngestJobs key={filterKey} address={address} filterKey={filterKey} reportCount={reportCount} />
    </section>
  );
}
