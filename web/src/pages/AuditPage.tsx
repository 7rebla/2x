import { type ReactElement, type SubmitEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { AuditTrail, auditObjectTypes } from "../components/AuditTrail.tsx";
import { AnimatedHeading } from "../components/TextMotion.tsx";
import { Button } from "../components/ui/Button.tsx";
import { Input, Select } from "../components/ui/fields.tsx";

/** Longest user name the API accepts as a filter (Django's username field). */
const ACTOR_MAX_LENGTH = 150;

interface AuditFilter {
  objectType?: string;
  actor?: string;
}

/**
 * Change log (address /audit): every change, newest first, filtered by object
 * type and user. Only "manage" sees this page (navigation.ts); a 403 of the
 * API shows "no permission" in the page, without a redirect.
 */
export function AuditPage(): ReactElement {
  const { t } = useTranslation("audit");
  const [objectType, setObjectType] = useState("");
  const [actor, setActor] = useState("");
  const [filter, setFilter] = useState<AuditFilter>({});
  const objectTypeId = useId();
  const actorId = useId();

  function apply(event: SubmitEvent<HTMLFormElement>): void {
    event.preventDefault();
    const trimmed = actor.trim();
    setFilter({
      ...(objectType === "" ? {} : { objectType }),
      ...(trimmed === "" ? {} : { actor: trimmed }),
    });
  }

  function reset(): void {
    setObjectType("");
    setActor("");
    setFilter({});
  }

  return (
    <section className="space-y-4">
      <AnimatedHeading text={t("heading")} />
      <p className="text-fg-muted">{t("intro")}</p>
      <form data-testid="audit-filter" onSubmit={apply} className="flex flex-wrap items-end gap-3">
        <fieldset className="contents">
          <legend className="sr-only">{t("filter.legend")}</legend>
          <div className="flex flex-col gap-1 text-sm">
            <label htmlFor={objectTypeId}>{t("filter.objectType")}</label>
            <Select
              id={objectTypeId}
              data-testid="audit-filter-object-type"
              value={objectType}
              onChange={(event) => {
                setObjectType(event.target.value);
              }}
            >
              <option value="">{t("filter.allObjectTypes")}</option>
              {auditObjectTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {t(`objectType.${type.textKey}`)}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex flex-col gap-1 text-sm">
            <label htmlFor={actorId}>{t("filter.actor")}</label>
            <Input
              id={actorId}
              data-testid="audit-filter-actor"
              type="text"
              value={actor}
              maxLength={ACTOR_MAX_LENGTH}
              placeholder={t("filter.actorHint")}
              autoComplete="off"
              onChange={(event) => {
                setActor(event.target.value);
              }}
            />
          </div>
          <Button type="submit" variant="primary" icon="filter">
            {t("filter.apply")}
          </Button>
          <Button type="button" icon="resetFilter" onClick={reset}>
            {t("filter.reset")}
          </Button>
        </fieldset>
      </form>
      <AuditTrail {...filter} />
    </section>
  );
}
