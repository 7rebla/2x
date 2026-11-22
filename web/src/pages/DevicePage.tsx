import { useQuery } from "@tanstack/react-query";
import { type ReactElement, type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { ApiError } from "../api/errors.ts";
import type { Device } from "../api/generated";
import { devicesRetrieveOptions } from "../api/generated/@tanstack/react-query.gen.ts";
import { DeviceFiles } from "../components/DeviceFiles.tsx";
import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { Loading } from "../components/Loading.tsx";
import { NotFound } from "../components/NotFound.tsx";
import { Icon } from "../icons/Icon.tsx";
import type { IconName } from "../icons/names.ts";
import { useRole } from "../session.ts";
import { deviceClassIcon, PLANT_ICON } from "./structure/deviceClass.ts";
import { DeviceForm, type FieldName } from "./structure/forms.tsx";
import { AnimatedHeading, MaskedTitle } from "../components/TextMotion.tsx";

/** The id from the address, or null if it cannot be a device id (then the page is NotFound). */
export function parseDeviceId(raw: string | undefined): number | null {
  if (raw === undefined || !/^[1-9][0-9]{0,15}$/.test(raw)) {
    return null;
  }
  const id = Number(raw);
  return Number.isSafeInteger(id) ? id : null;
}

/** One device with all its fields (address /devices/:deviceId). */
export function DevicePage(): ReactElement {
  const { deviceId } = useParams();
  const id = parseDeviceId(deviceId);
  if (id === null) {
    return <NotFound />;
  }
  // The key starts a fresh page (closed form) for another device.
  return <DeviceDetails key={id} id={id} />;
}

function DeviceDetails({ id }: { id: number }): ReactElement {
  const { t } = useTranslation("nav");
  const query = useQuery(devicesRetrieveOptions({ path: { id } }));

  if (query.data !== undefined) {
    return <DeviceView device={query.data} error={query.error} />;
  }
  if (query.error instanceof ApiError && query.error.kind === "http" && query.error.status === 404) {
    return <NotFound />;
  }
  return (
    <section className="space-y-4">
      <AnimatedHeading text={t("device")} />
      {query.isError ? <ErrorMessage error={query.error} /> : <Loading />}
    </section>
  );
}

/** Fields in the order shown; site, area and plant appear in the breadcrumb. */
const TEXT_FIELDS = [
  "key",
  "name",
  "device_class",
  "manufacturer",
  "model",
  "software_version",
  "ip_address",
  "address_source",
  "protocols",
  "notes",
] as const satisfies readonly (FieldName & keyof Device)[];

/** Identifiers, addresses and versions: tabular figures with a slashed zero (no monospace). */
const IDENTIFIER_FIELDS = new Set<FieldName>(["key", "ip_address", "software_version"]);

function DeviceView({ device, error }: { device: Device; error: unknown }): ReactElement {
  const { t, i18n } = useTranslation(["assets", "nav"]);
  const { canManage } = useRole();
  const [editing, setEditing] = useState(false);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium", timeStyle: "short" });
  const icon = deviceClassIcon(device.device_class);

  return (
    <section className="space-y-4">
      <nav aria-label={t("assets:device.breadcrumb")} data-testid="device-breadcrumb">
        <ol className="flex flex-wrap gap-x-2 text-sm text-fg-muted">
          <Crumb icon="structure">
            <Link to="/" className="text-accent underline hover:text-accent-strong">
              {t("nav:structure")}
            </Link>
          </Crumb>
          <Crumb icon="site" testId="breadcrumb-site">{device.site.name}</Crumb>
          <Crumb icon="area" testId="breadcrumb-area">{device.area.name}</Crumb>
          <Crumb icon={PLANT_ICON} testId="breadcrumb-plant">
            {device.plant.name} <span className="tabular-nums slashed-zero">({device.plant.key})</span>
          </Crumb>
          <li data-testid="breadcrumb-device" aria-current="page" className="font-semibold text-fg">
            <Icon name={icon} className="mr-1" decorative />
            {device.name}
          </li>
        </ol>
      </nav>

      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* The class icon before the name; the class itself is written out in the field list. */}
        <div data-testid="device-heading" className="flex min-w-0 items-center gap-2">
          <Icon name={icon} size={24} className="text-fg-muted" decorative />
          <MaskedTitle text={device.name} testId="device-title" />
        </div>
        {canManage && !editing ? (
          <button
            type="button"
            aria-label={t("assets:actions.editDevice", { name: device.name })}
            onClick={() => {
              setEditing(true);
            }}
            className="inline-flex items-center gap-2 rounded bg-accent px-4 py-2 text-on-accent hover:bg-accent-strong"
          >
            <Icon name="edit" size={20} decorative />
            {t("assets:actions.edit")}
          </button>
        ) : null}
      </div>

      {/* A failed reload keeps the last data on screen and says so. */}
      {error === null ? null : <ErrorMessage error={error} />}

      {editing ? (
        <DeviceForm
          device={device}
          plantId={device.plant.id}
          onDone={() => {
            setEditing(false);
          }}
        />
      ) : null}

      <dl
        aria-label={t("assets:device.fieldsLabel")}
        className="grid grid-cols-1 gap-x-6 gap-y-2 rounded border border-line bg-surface p-4 sm:grid-cols-[max-content_1fr]"
      >
        <Field label={t("assets:fields.site")} testId="device-site">
          {device.site.name}
        </Field>
        <Field label={t("assets:fields.area")} testId="device-area">
          {device.area.name}
        </Field>
        <Field label={t("assets:fields.plant")} testId="device-plant">
          {device.plant.name} <span className="tabular-nums slashed-zero">({device.plant.key})</span>
        </Field>
        {TEXT_FIELDS.map((field) => {
          // The class is shown by its label (E-53), the icon stays decorative (work order 074).
          const value = field === "device_class" ? t(`assets:deviceClass.${device.device_class}`) : device[field];
          return (
            <Field
              key={field}
              label={t(`assets:fields.${field}`)}
              testId={`device-${field}`}
              identifier={IDENTIFIER_FIELDS.has(field)}
            >
              {value === null || value === "" ? t("assets:device.notSet") : value}
            </Field>
          );
        })}
        <Field label={t("assets:fields.created_at")} testId="device-created_at">
          <time dateTime={device.created_at}>{dateFormat.format(new Date(device.created_at))}</time>
        </Field>
        <Field label={t("assets:fields.updated_at")} testId="device-updated_at">
          <time dateTime={device.updated_at}>{dateFormat.format(new Date(device.updated_at))}</time>
        </Field>
      </dl>

      <DeviceFiles deviceId={device.id} />
    </section>
  );
}

/** One level of the breadcrumb, with the icon of its kind (site, area, plant). */
function Crumb({ icon, testId, children }: { icon: IconName; testId?: string; children: ReactNode }): ReactElement {
  return (
    <li data-testid={testId} className="after:ml-2 after:content-['›']">
      <Icon name={icon} className="mr-1" decorative />
      {children}
    </li>
  );
}

function Field({
  label,
  testId,
  identifier = false,
  children,
}: {
  label: string;
  testId: string;
  identifier?: boolean;
  children: ReactNode;
}): ReactElement {
  return (
    <>
      <dt className="text-fg-muted">{label}</dt>
      {/* pre-wrap keeps the line breaks of notes and address sources; long words break. */}
      <dd data-testid={testId} className={`whitespace-pre-wrap break-words ${identifier ? "tabular-nums slashed-zero" : ""}`}>
        {children}
      </dd>
    </>
  );
}
