import { useEffect, useState } from "react";

import { fetchDistinctValues, fetchPeople, type DistinctOption, type PersonRef } from "../api/bids";

const NAME_FIELDS = [
  "client",
  "cam",
  "sales_resource",
  "bid_manager",
  "stage",
  "initiation_mode",
  "procurement_type",
  "security_mode",
  "submission_status",
  "result",
  "bg_bank",
] as const;

export interface FormOptions {
  names: Record<(typeof NAME_FIELDS)[number], string[]>;
  teams: DistinctOption[];
  people: PersonRef[];
  loading: boolean;
}

const EMPTY_NAMES = Object.fromEntries(NAME_FIELDS.map((f) => [f, []])) as unknown as FormOptions["names"];

/** Everything the create/edit form's comboboxes and selects need, loaded
 * once when the form mounts. Small enough (a few dozen to ~160 rows each)
 * to fetch in full rather than searching server-side per keystroke. */
export function useFormOptions(): FormOptions {
  const [names, setNames] = useState<FormOptions["names"]>(EMPTY_NAMES);
  const [teams, setTeams] = useState<DistinctOption[]>([]);
  const [people, setPeople] = useState<PersonRef[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      Promise.all(NAME_FIELDS.map((field) => fetchDistinctValues(field).then((opts) => [field, opts] as const))),
      fetchDistinctValues("team"),
      fetchPeople(),
    ]).then(([nameEntries, teamOptions, peopleList]) => {
      if (cancelled) return;
      setNames(
        Object.fromEntries(nameEntries.map(([field, opts]) => [field, opts.map((o) => o.label)])) as FormOptions["names"]
      );
      setTeams(teamOptions);
      setPeople(peopleList);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  return { names, teams, people, loading };
}
