// Forms to create and edit sites, areas, plants and devices (React 19 form
// actions with useActionState, no form library).
//
// Every form sends all its fields; a 400 answer shows DRF's messages at the
// fields (save.ts). After saving, the cached data is fetched again and the
// form closes.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactElement, type ReactNode, useActionState, useId } from "react";
import { useTranslation } from "react-i18next";

import {
  areasCreateMutation,
  areasListOptions,
  areasUpdateMutation,
  devicesCreateMutation,
  devicesUpdateMutation,
  plantsCreateMutation,
  plantsListOptions,
  plantsUpdateMutation,
  sitesCreateMutation,
  sitesListOptions,
  sitesUpdateMutation,
} from "../../api/generated/@tanstack/react-query.gen.ts";
import type { Area, Device, Plant, Site } from "../../api/generated";
import { ErrorMessage } from "../../components/ErrorMessage.tsx";
import { Loading } from "../../components/Loading.tsx";
import type assetsCatalog from "../../locales/en/assets.json";
import { DEFAULT_DEVICE_CLASS, deviceClasses, isDeviceClass } from "./deviceClass.ts";
import { type FieldErrors, reloadAfterSave, save } from "./save.ts";

/** Name of a field as sent to the API; its label is fields.<name> in assets.json. */
export type FieldName = keyof typeof assetsCatalog.fields;

type FormValues = Readonly<Partial<Record<FieldName, string>>>;

interface FormState {
  /** What was last sent (or the start values), so that a rejected entry stays in the fields. */
  readonly values: FormValues;
  readonly fieldErrors: FieldErrors;
  /** The API answered 400. */
  readonly invalid: boolean;
  /** Any other failure (no permission, no answer …). */
  readonly failure: { readonly error: unknown } | null;
  /**
   * Counts the submissions. The fields are mounted afresh for each one, so
   * that all of them show `values`: React resets uncontrolled fields after a
   * form action, and a <select> would otherwise fall back to the option of
   * its first render (a changed parent would be lost after a 400).
   */
  readonly attempt: number;
}

function readValues(formData: FormData, fields: readonly FieldName[]): FormValues {
  const values: Partial<Record<FieldName, string>> = {};
  for (const field of fields) {
    const value = formData.get(field);
    values[field] = typeof value === "string" ? value : "";
  }
  return values;
}

/** Id of a parent from a select; an empty choice becomes NaN, which JSON sends as null and the API rejects at the field. */
function parentId(value: string | undefined): number {
  return value === undefined || value === "" ? Number.NaN : Number(value);
}

function text(values: FormValues, field: FieldName): string {
  return values[field] ?? "";
}

/** The form action: save, then reload the data and report success, or keep the values and show the errors. */
function useSaveAction(
  fields: readonly FieldName[],
  initialValues: FormValues,
  send: (values: FormValues, fetchFn: typeof fetch) => Promise<unknown>,
  onSaved: () => void,
): [FormState, (formData: FormData) => void, boolean] {
  const queryClient = useQueryClient();
  return useActionState<FormState, FormData>(
    async (previous, formData) => {
      const values = readValues(formData, fields);
      const attempt = previous.attempt + 1;
      const outcome = await save((fetchFn) => send(values, fetchFn));
      switch (outcome.kind) {
        case "saved":
          await reloadAfterSave(queryClient);
          onSaved();
          return { values, fieldErrors: {}, invalid: false, failure: null, attempt };
        case "invalid":
          return { values, fieldErrors: outcome.fieldErrors, invalid: true, failure: null, attempt };
        case "failed":
          return { values, fieldErrors: {}, invalid: false, failure: { error: outcome.error }, attempt };
      }
    },
    { values: initialValues, fieldErrors: {}, invalid: false, failure: null, attempt: 0 },
  );
}

const inputClass =
  "w-full rounded border border-slate-300 bg-white px-3 py-2 aria-[invalid=true]:border-red-500";

function FieldFrame({
  name,
  errors,
  children,
}: {
  name: FieldName;
  errors: readonly string[];
  children: (props: { id: string; invalid: boolean; describedBy: string | undefined }) => ReactNode;
}): ReactElement {
  const { t } = useTranslation("assets");
  const id = useId();
  const errorId = `${id}-error`;
  const invalid = errors.length > 0;
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm text-slate-600">
        {t(`fields.${name}`)}
      </label>
      {children({ id, invalid, describedBy: invalid ? errorId : undefined })}
      {invalid ? (
        <ul id={errorId} data-testid={`field-error-${name}`} className="text-sm text-red-800">
          {errors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function TextField({
  name,
  state,
  multiline = false,
  monospace = false,
}: {
  name: FieldName;
  state: FormState;
  multiline?: boolean;
  monospace?: boolean;
}): ReactElement {
  const className = monospace ? `${inputClass} font-mono` : inputClass;
  return (
    <FieldFrame name={name} errors={state.fieldErrors[name] ?? []}>
      {({ id, invalid, describedBy }) =>
        multiline ? (
          <textarea
            id={id}
            name={name}
            rows={4}
            defaultValue={text(state.values, name)}
            aria-invalid={invalid}
            aria-describedby={describedBy}
            className={className}
          />
        ) : (
          <input
            id={id}
            name={name}
            type="text"
            autoComplete="off"
            spellCheck={false}
            defaultValue={text(state.values, name)}
            aria-invalid={invalid}
            aria-describedby={describedBy}
            className={className}
          />
        )
      }
    </FieldFrame>
  );
}

interface Choice {
  readonly id: number;
  readonly label: string;
}

function SelectField({
  name,
  state,
  choices,
}: {
  name: FieldName;
  state: FormState;
  choices: readonly Choice[];
}): ReactElement {
  const { t } = useTranslation("assets");
  return (
    <FieldFrame name={name} errors={state.fieldErrors[name] ?? []}>
      {({ id, invalid, describedBy }) => (
        <select
          id={id}
          name={name}
          defaultValue={text(state.values, name)}
          aria-invalid={invalid}
          aria-describedby={describedBy}
          className={inputClass}
        >
          <option value="">{t("form.choose")}</option>
          {choices.map((choice) => (
            <option key={choice.id} value={String(choice.id)}>
              {choice.label}
            </option>
          ))}
        </select>
      )}
    </FieldFrame>
  );
}

/** The device class as a fixed choice (E-53); there is no empty option, a new device starts as "other". */
function DeviceClassField({ state }: { state: FormState }): ReactElement {
  const { t } = useTranslation("assets");
  return (
    <FieldFrame name="device_class" errors={state.fieldErrors.device_class ?? []}>
      {({ id, invalid, describedBy }) => (
        <select
          id={id}
          name="device_class"
          defaultValue={text(state.values, "device_class")}
          aria-invalid={invalid}
          aria-describedby={describedBy}
          className={inputClass}
        >
          {deviceClasses.map((value) => (
            <option key={value} value={value}>
              {t(`deviceClass.${value}`)}
            </option>
          ))}
        </select>
      )}
    </FieldFrame>
  );
}

/** Frame of every form: title, errors that belong to no field, the fields, Save and Cancel. */
function FormShell({
  title,
  fields,
  state,
  action,
  pending,
  onCancel,
  children,
}: {
  title: string;
  fields: readonly FieldName[];
  state: FormState;
  action: (formData: FormData) => void;
  pending: boolean;
  onCancel: () => void;
  children: ReactNode;
}): ReactElement {
  const { t } = useTranslation("assets");
  const titleId = useId();
  const known = new Set<string>(fields);
  const otherErrors = Object.entries(state.fieldErrors)
    .filter(([field]) => !known.has(field))
    .flatMap(([, list]) => list);
  return (
    <form
      action={action}
      noValidate
      aria-labelledby={titleId}
      data-testid="structure-form"
      className="space-y-3 rounded border border-slate-300 bg-white p-4"
    >
      <h3 id={titleId} className="font-semibold">
        {title}
      </h3>
      {state.invalid ? (
        <div role="alert" data-testid="form-invalid" className="rounded border border-red-300 bg-red-50 p-3 text-red-800">
          <p>{t("form.invalid")}</p>
          {otherErrors.length > 0 ? (
            <ul className="mt-1 list-disc pl-5 text-sm" aria-label={t("form.otherErrors")}>
              {otherErrors.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
      {state.failure === null ? null : <ErrorMessage error={state.failure.error} />}
      {/* Fresh fields per submission, see FormState.attempt. */}
      <div key={state.attempt} className="space-y-3">
        {children}
      </div>
      <div className="flex gap-2">
        <button type="submit" disabled={pending} className="rounded bg-slate-800 px-4 py-2 text-white disabled:opacity-50">
          {pending ? t("actions.saving") : t("actions.save")}
        </button>
        <button type="button" onClick={onCancel} className="rounded border border-slate-300 px-4 py-2">
          {t("actions.cancel")}
        </button>
      </div>
    </form>
  );
}

interface FormProps {
  /** Called after saving (the data is fetched again by then) and on Cancel. */
  readonly onDone: () => void;
}

const SITE_FIELDS: readonly FieldName[] = ["name"];

/** Create a site (site undefined) or edit one. */
export function SiteForm({ site, onDone }: FormProps & { site?: Site }): ReactElement {
  const { t } = useTranslation("assets");
  const create = useMutation(sitesCreateMutation());
  const update = useMutation(sitesUpdateMutation());
  const [state, action, pending] = useSaveAction(
    SITE_FIELDS,
    { name: site?.name ?? "" },
    (values, fetchFn) => {
      const body = { name: text(values, "name") };
      return site === undefined
        ? create.mutateAsync({ body, fetch: fetchFn })
        : update.mutateAsync({ path: { id: site.id }, body, fetch: fetchFn });
    },
    onDone,
  );
  return (
    <FormShell
      title={site === undefined ? t("form.createSite") : t("form.editSite")}
      fields={SITE_FIELDS}
      state={state}
      action={action}
      pending={pending}
      onCancel={onDone}
    >
      <TextField name="name" state={state} />
    </FormShell>
  );
}

const AREA_FIELDS: readonly FieldName[] = ["site", "name"];

/** Create an area in the site `siteId` (area undefined) or edit one; the site can be changed. */
export function AreaForm({ area, siteId, onDone }: FormProps & { area?: Area; siteId: number }): ReactElement {
  const { t } = useTranslation("assets");
  const sites = useQuery(sitesListOptions());
  const create = useMutation(areasCreateMutation());
  const update = useMutation(areasUpdateMutation());
  const [state, action, pending] = useSaveAction(
    AREA_FIELDS,
    { site: String(area?.site ?? siteId), name: area?.name ?? "" },
    (values, fetchFn) => {
      const body = { site: parentId(values.site), name: text(values, "name") };
      return area === undefined
        ? create.mutateAsync({ body, fetch: fetchFn })
        : update.mutateAsync({ path: { id: area.id }, body, fetch: fetchFn });
    },
    onDone,
  );
  if (sites.isPending) {
    return <Loading />;
  }
  if (sites.isError) {
    return <ErrorMessage error={sites.error} />;
  }
  return (
    <FormShell
      title={area === undefined ? t("form.createArea") : t("form.editArea")}
      fields={AREA_FIELDS}
      state={state}
      action={action}
      pending={pending}
      onCancel={onDone}
    >
      <SelectField name="site" state={state} choices={siteChoices(sites.data)} />
      <TextField name="name" state={state} />
    </FormShell>
  );
}

const PLANT_FIELDS: readonly FieldName[] = ["area", "key", "name", "notes"];

/** Create a plant in the area `areaId` (plant undefined) or edit one; the area can be changed. */
export function PlantForm({ plant, areaId, onDone }: FormProps & { plant?: Plant; areaId: number }): ReactElement {
  const { t } = useTranslation("assets");
  const sites = useQuery(sitesListOptions());
  const areas = useQuery(areasListOptions());
  const create = useMutation(plantsCreateMutation());
  const update = useMutation(plantsUpdateMutation());
  const [state, action, pending] = useSaveAction(
    PLANT_FIELDS,
    {
      area: String(plant?.area ?? areaId),
      key: plant?.key ?? "",
      name: plant?.name ?? "",
      notes: plant?.notes ?? "",
    },
    (values, fetchFn) => {
      const body = {
        area: parentId(values.area),
        key: text(values, "key"),
        name: text(values, "name"),
        notes: text(values, "notes"),
      };
      return plant === undefined
        ? create.mutateAsync({ body, fetch: fetchFn })
        : update.mutateAsync({ path: { id: plant.id }, body, fetch: fetchFn });
    },
    onDone,
  );
  if (sites.isPending || areas.isPending) {
    return <Loading />;
  }
  if (sites.isError || areas.isError) {
    return <ErrorMessage error={sites.error ?? areas.error} />;
  }
  return (
    <FormShell
      title={plant === undefined ? t("form.createPlant") : t("form.editPlant")}
      fields={PLANT_FIELDS}
      state={state}
      action={action}
      pending={pending}
      onCancel={onDone}
    >
      <SelectField name="area" state={state} choices={areaChoices(sites.data, areas.data)} />
      <TextField name="key" state={state} monospace />
      <TextField name="name" state={state} />
      <TextField name="notes" state={state} multiline />
    </FormShell>
  );
}

const DEVICE_FIELDS: readonly FieldName[] = [
  "plant",
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
];

/** Create a device in the plant `plantId` (device undefined) or edit one; the plant can be changed. */
export function DeviceForm({
  device,
  plantId,
  onDone,
}: FormProps & { device?: Device; plantId: number }): ReactElement {
  const { t } = useTranslation("assets");
  const sites = useQuery(sitesListOptions());
  const areas = useQuery(areasListOptions());
  const plants = useQuery(plantsListOptions());
  const create = useMutation(devicesCreateMutation());
  const update = useMutation(devicesUpdateMutation());
  const [state, action, pending] = useSaveAction(
    DEVICE_FIELDS,
    {
      plant: String(device?.plant.id ?? plantId),
      key: device?.key ?? "",
      name: device?.name ?? "",
      device_class: device?.device_class ?? DEFAULT_DEVICE_CLASS,
      manufacturer: device?.manufacturer ?? "",
      model: device?.model ?? "",
      software_version: device?.software_version ?? "",
      ip_address: device?.ip_address ?? "",
      address_source: device?.address_source ?? "",
      protocols: device?.protocols ?? "",
      notes: device?.notes ?? "",
    },
    (values, fetchFn) => {
      const ipAddress = text(values, "ip_address").trim();
      const deviceClass = text(values, "device_class");
      const body = {
        plant: parentId(values.plant),
        key: text(values, "key"),
        name: text(values, "name"),
        // The select offers only known classes; anything else is left out (the API keeps the stored one).
        ...(isDeviceClass(deviceClass) ? { device_class: deviceClass } : {}),
        manufacturer: text(values, "manufacturer"),
        model: text(values, "model"),
        software_version: text(values, "software_version"),
        // An empty field means "no address" (null); the API checks everything else.
        ip_address: ipAddress === "" ? null : ipAddress,
        address_source: text(values, "address_source"),
        protocols: text(values, "protocols"),
        notes: text(values, "notes"),
      };
      return device === undefined
        ? create.mutateAsync({ body, fetch: fetchFn })
        : update.mutateAsync({ path: { id: device.id }, body, fetch: fetchFn });
    },
    onDone,
  );
  if (sites.isPending || areas.isPending || plants.isPending) {
    return <Loading />;
  }
  if (sites.isError || areas.isError || plants.isError) {
    return <ErrorMessage error={sites.error ?? areas.error ?? plants.error} />;
  }
  return (
    <FormShell
      title={device === undefined ? t("form.createDevice") : t("form.editDevice")}
      fields={DEVICE_FIELDS}
      state={state}
      action={action}
      pending={pending}
      onCancel={onDone}
    >
      <SelectField name="plant" state={state} choices={plantChoices(sites.data, areas.data, plants.data)} />
      <TextField name="key" state={state} monospace />
      <TextField name="name" state={state} />
      <DeviceClassField state={state} />
      <TextField name="manufacturer" state={state} />
      <TextField name="model" state={state} />
      <TextField name="software_version" state={state} />
      <TextField name="ip_address" state={state} monospace />
      <TextField name="address_source" state={state} multiline />
      <TextField name="protocols" state={state} />
      <TextField name="notes" state={state} multiline />
    </FormShell>
  );
}

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

function sortedChoices(choices: Choice[]): Choice[] {
  return choices.sort((left, right) => collator.compare(left.label, right.label));
}

function siteChoices(sites: readonly Site[]): Choice[] {
  return sortedChoices(sites.map((site) => ({ id: site.id, label: site.name })));
}

function areaLabel(sitesById: ReadonlyMap<number, Site>, area: Area): string {
  const site = sitesById.get(area.site);
  return site === undefined ? area.name : `${site.name} › ${area.name}`;
}

function areaChoices(sites: readonly Site[], areas: readonly Area[]): Choice[] {
  const sitesById = new Map(sites.map((site) => [site.id, site]));
  return sortedChoices(areas.map((area) => ({ id: area.id, label: areaLabel(sitesById, area) })));
}

function plantChoices(sites: readonly Site[], areas: readonly Area[], plants: readonly Plant[]): Choice[] {
  const sitesById = new Map(sites.map((site) => [site.id, site]));
  const areasById = new Map(areas.map((area) => [area.id, area]));
  return sortedChoices(
    plants.map((plant) => {
      const area = areasById.get(plant.area);
      const own = `${plant.name} (${plant.key})`;
      return { id: plant.id, label: area === undefined ? own : `${areaLabel(sitesById, area)} › ${own}` };
    }),
  );
}
