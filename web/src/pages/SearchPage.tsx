// Search page (address /search, work order 054): one field for a term, an
// identifier or a question, optionally limited to one device.
//
// The search text and the device stand in the browser address
// (/search?q=…&device=…, question 1 of work order 052, E-54), so a search can
// be linked, reloaded and reached with Back. The API (GET /api/v1/search/)
// drops the query part from its access log (work order 052). routes.tsx loads
// this page with lazy(), like the map.
import { useQuery } from "@tanstack/react-query";
import { type ReactElement, type SubmitEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";

import type { SearchData, SearchResult } from "../api/generated";
import { devicesListOptions, searchOptions } from "../api/generated/@tanstack/react-query.gen.ts";
import { devicesByPlant } from "../components/devicesByPlant.ts";
import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { parseId } from "../components/files/format.ts";
import { Loading } from "../components/Loading.tsx";
import { AnimatedHeading } from "../components/TextMotion.tsx";
import { usePageTitle } from "../hooks/usePageTitle.ts";
import { Button } from "../components/ui/Button.tsx";
import { Input, Select } from "../components/ui/fields.tsx";
import { Icon } from "../icons/Icon.tsx";
import { SearchHitView } from "./search/SearchHitView.tsx";

/** Longest search text the API accepts (characters after trimming, work order 052). */
export const QUERY_MAX_LENGTH = 500;

/** What the address asks for: the trimmed search text ("" for none) and the device id (null for all). */
export interface SearchAddress {
  readonly q: string;
  readonly device: number | null;
}

/** Reads ?q= and ?device= from the address; a device value that cannot be an id counts as "all devices". */
export function readSearchAddress(params: URLSearchParams): SearchAddress {
  return {
    q: (params.get("q") ?? "").trim(),
    device: parseId(params.get("device") ?? undefined),
  };
}

/** The address parameters of a search; empty values are left out. */
export function searchAddressParams({ q, device }: SearchAddress): URLSearchParams {
  const params = new URLSearchParams();
  if (q !== "") {
    params.set("q", q);
  }
  if (device !== null) {
    params.set("device", String(device));
  }
  return params;
}

function SearchForm({
  address,
  onSearch,
}: {
  address: SearchAddress;
  onSearch: (address: SearchAddress) => void;
}): ReactElement {
  const { t } = useTranslation("search");
  const [query, setQuery] = useState(address.q);
  const [device, setDevice] = useState(address.device === null ? "" : String(address.device));
  const devices = useQuery(devicesListOptions());
  const queryId = useId();
  const deviceId = useId();

  function submit(event: SubmitEvent<HTMLFormElement>): void {
    event.preventDefault();
    onSearch({ q: query.trim(), device: parseId(device === "" ? undefined : device) });
  }

  const known = devices.data ?? [];
  const chosenUnknown = address.device !== null && devices.isSuccess && !known.some((item) => item.id === address.device);

  return (
    <form
      role="search"
      aria-label={t("form.label")}
      data-testid="search-form"
      onSubmit={submit}
      className="space-y-2"
    >
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex min-w-64 flex-1 flex-col gap-1 text-sm">
          <label htmlFor={queryId}>{t("form.query")}</label>
          <Input
            id={queryId}
            data-testid="search-query"
            type="search"
            value={query}
            maxLength={QUERY_MAX_LENGTH}
            placeholder={t("form.queryHint")}
            autoComplete="off"
            enterKeyHint="search"
            onChange={(event) => {
              setQuery(event.target.value);
            }}
          />
        </div>
        <div className="flex flex-col gap-1 text-sm">
          <label htmlFor={deviceId}>{t("form.device")}</label>
          <Select
            id={deviceId}
            data-testid="search-device"
            className="max-w-72"
            value={device}
            aria-busy={devices.isPending}
            onChange={(event) => {
              setDevice(event.target.value);
            }}
          >
            <option value="">{t("form.allDevices")}</option>
            {chosenUnknown ? (
              <option value={String(address.device)}>{t("form.unknownDevice", { id: address.device })}</option>
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
        <Button type="submit" variant="primary" icon="search">
          {t("form.submit")}
        </Button>
      </div>
      {devices.isError ? <ErrorMessage error={devices.error} /> : null}
    </form>
  );
}

/** How the search by meaning took part: nothing for "used", a calm line for "disabled", a hint for "unavailable". */
function SemanticNotice({ semantic }: { semantic: SearchResult["semantic"] }): ReactElement | null {
  const { t } = useTranslation("search");
  if (semantic === "unavailable") {
    return (
      <p
        role="status"
        data-testid="search-semantic-unavailable"
        className="rounded border border-warning-line bg-warning-soft p-3 text-warning"
      >
        <Icon name="warning" className="mr-2" decorative />
        {t("semantic.unavailable")}
      </p>
    );
  }
  if (semantic === "disabled") {
    // AI features switched off (E-59): a normal state, not an error.
    return (
      <p data-testid="search-semantic-disabled" className="text-sm text-fg-muted">
        {t("semantic.disabled")}
      </p>
    );
  }
  return null;
}

function SearchResults({ address }: { address: SearchAddress }): ReactElement {
  const { t } = useTranslation("search");
  const query: SearchData["query"] = { q: address.q };
  if (address.device !== null) {
    query.device = [address.device];
  }
  const result = useQuery({ ...searchOptions({ query }), enabled: address.q !== "" });

  if (address.q === "") {
    return (
      <p data-testid="search-empty" className="text-fg-muted">
        {t("empty")}
      </p>
    );
  }
  if (result.isPending) {
    return <Loading label={t("loading")} />;
  }
  if (result.isError) {
    return <ErrorMessage error={result.error} />;
  }

  const { semantic, hits } = result.data;
  return (
    <div data-testid="search-results" data-semantic={semantic} className="space-y-3">
      <SemanticNotice semantic={semantic} />
      {hits.length === 0 ? (
        <p role="status" data-testid="search-no-hits" className="text-fg-muted">
          {t("noHits")}
        </p>
      ) : (
        <>
          <p role="status" data-testid="search-count" className="text-sm text-fg-muted">
            {t("hitCount", { count: hits.length })}
          </p>
          <ol aria-label={t("resultsLabel")} className="space-y-3">
            {hits.map((hit) => (
              <SearchHitView key={hit.section_id} hit={hit} />
            ))}
          </ol>
        </>
      )}
    </div>
  );
}

/** Search in the ingested documents (role "read"). */
export function SearchPage(): ReactElement {
  const { t } = useTranslation(["nav", "search"]);
  usePageTitle(t("nav:search"));
  const [params, setParams] = useSearchParams();
  const address = readSearchAddress(params);
  // A new address (a search, Back, a link) starts the form again with its values.
  const formKey = searchAddressParams(address).toString();

  return (
    <section className="space-y-4">
      <AnimatedHeading text={t("nav:search")} />
      <p className="text-fg-muted">{t("search:intro")}</p>
      <SearchForm
        key={formKey}
        address={address}
        onSearch={(next) => {
          setParams(searchAddressParams(next));
        }}
      />
      <SearchResults address={address} />
    </section>
  );
}
