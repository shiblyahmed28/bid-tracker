import type { ChoiceListItem } from "../api/settings";

export type RailItem =
  | { kind: "choice"; key: string; label: string; valuesCount: number }
  | { kind: "reference"; key: "clients" | "people" | "teams"; label: string };

// The exact order given in the phase spec — not alphabetical (which is how
// the API returns ChoiceList rows), so it's re-sorted client-side.
const CHOICE_LIST_ORDER = [
  "stage",
  "security_mode",
  "initiation_mode",
  "procurement_type",
  "issuing_bank",
  "result",
  "submission_status",
  "delivery_type",
  // §Phase 19 item 2 — BidCostLine.category, admin-managed like every other
  // list here, though the cost-line management UI itself isn't built yet.
  "cost_category",
];

export function buildRail(choiceLists: ChoiceListItem[]): RailItem[] {
  const byKey = new Map(choiceLists.map((cl) => [cl.key, cl]));
  const choiceItems: RailItem[] = CHOICE_LIST_ORDER.filter((key) => byKey.has(key)).map((key) => {
    const cl = byKey.get(key)!;
    return { kind: "choice", key: cl.key, label: cl.label, valuesCount: cl.values_count };
  });

  return [
    ...choiceItems,
    { kind: "reference", key: "clients", label: "Clients" },
    { kind: "reference", key: "people", label: "People" },
    { kind: "reference", key: "teams", label: "Teams" },
  ];
}
