import type { BidListItem } from "../api/bids";
import { formatDMY } from "../lib/dateUtils";

export type ColumnGroup = "Core" | "New fields" | "People" | "Dates" | "Financial" | "Status";
export type ColumnKind = "num" | "enum" | "text" | "list" | "money" | "date" | "period";

export interface ColumnDef {
  key: string;
  label: string;
  group: ColumnGroup;
  kind: ColumnKind;
  defaultVisible: boolean;
  isNew?: boolean;
  /** The BidFilter query param this column filters on, if any (§13: only
   * enum/text/list/money columns get a filter — date/num/period don't). */
  filterParam?: string;
  render: (bid: BidListItem) => string;
}

function dateTimeCell(date: string | null, time: string | null): string {
  if (!date) return "—";
  return time ? `${formatDMY(date)}, ${time.slice(0, 5)}` : formatDMY(date);
}

function moneyCell(raw: string): string {
  return raw || "—";
}

function nameOrDash(ref: { canonical_name: string } | null): string {
  return ref?.canonical_name ?? "—";
}

/** The 28 sheet-mirrored columns (§5/§13) plus `initiation_date` — a real,
 * distinct sheet column (§5 #13) that CLAUDE.md's own model listing omits
 * but that Phase 4/5 preserved rather than silently dropping. */
export const COLUMNS: ColumnDef[] = [
  {
    key: "serial",
    label: "SL",
    group: "Core",
    kind: "num",
    defaultVisible: true,
    render: (b) => (b.serial ?? "—").toString(),
  },
  {
    key: "client",
    label: "Client",
    group: "Core",
    kind: "enum",
    defaultVisible: true,
    filterParam: "client",
    render: (b) => b.client.name,
  },
  {
    key: "description",
    label: "Description",
    group: "Core",
    kind: "text",
    defaultVisible: false,
    filterParam: "description",
    render: (b) => b.description || "—",
  },
  {
    key: "team",
    label: "Team",
    group: "New fields",
    kind: "enum",
    defaultVisible: true,
    isNew: true,
    filterParam: "team",
    render: (b) => b.team?.name ?? "—",
  },
  {
    key: "stage",
    label: "Stage",
    group: "Core",
    kind: "enum",
    defaultVisible: true,
    filterParam: "stage",
    render: (b) => b.stage || "—",
  },
  {
    key: "procurement_type",
    label: "Procurement type",
    group: "Core",
    kind: "enum",
    defaultVisible: false,
    filterParam: "procurement_type",
    render: (b) => b.procurement_type || "—",
  },
  {
    key: "initiation_mode",
    label: "Initiation mode",
    group: "Core",
    kind: "enum",
    defaultVisible: false,
    filterParam: "initiation_mode",
    render: (b) => b.initiation_mode || "—",
  },
  {
    key: "delivery_type",
    label: "Delivery type",
    group: "Core",
    kind: "enum",
    defaultVisible: false,
    filterParam: "delivery_type",
    render: (b) => [b.is_goods && "Goods", b.is_works && "Works", b.is_service && "Service"].filter(Boolean).join(", ") || "—",
  },
  {
    key: "tender_id",
    label: "Tender ID",
    group: "Core",
    kind: "text",
    defaultVisible: false,
    filterParam: "tender_id",
    render: (b) => b.tender_id || "—",
  },
  {
    key: "cam",
    label: "CAM",
    group: "People",
    kind: "enum",
    defaultVisible: false,
    filterParam: "cam",
    render: (b) => nameOrDash(b.cam),
  },
  {
    key: "sales_resource",
    label: "Sales resource",
    group: "People",
    kind: "enum",
    defaultVisible: false,
    filterParam: "sales_resource",
    render: (b) => nameOrDash(b.sales_resource),
  },
  {
    key: "bid_manager",
    label: "Bid manager",
    group: "People",
    kind: "enum",
    defaultVisible: true,
    filterParam: "bid_manager",
    render: (b) => nameOrDash(b.bid_manager),
  },
  {
    key: "engaged_resources",
    label: "Engaged resources",
    group: "New fields",
    kind: "list",
    defaultVisible: true,
    isNew: true,
    filterParam: "engaged_resources",
    render: (b) => (b.engaged_resources.length ? b.engaged_resources.map((p) => p.canonical_name).join(", ") : "—"),
  },
  {
    key: "engagement_period",
    label: "Engagement period",
    group: "New fields",
    kind: "period",
    defaultVisible: false,
    isNew: true,
    render: (b) => (b.engagement_from ? `${formatDMY(b.engagement_from)} → ${formatDMY(b.engagement_to)}` : "—"),
  },
  {
    key: "engagement_days",
    label: "Engagement days",
    group: "New fields",
    kind: "num",
    defaultVisible: false,
    isNew: true,
    render: (b) => (b.engagement_days != null ? `${b.engagement_days}d` : "—"),
  },
  {
    key: "initiation_date",
    label: "Initiation date",
    group: "Dates",
    kind: "date",
    defaultVisible: false,
    render: (b) => formatDMY(b.initiation_date),
  },
  {
    key: "published_date",
    label: "Published",
    group: "Dates",
    kind: "date",
    defaultVisible: true,
    render: (b) => formatDMY(b.published_date),
  },
  {
    key: "prebid_date",
    label: "Pre-bid",
    group: "Dates",
    kind: "date",
    defaultVisible: false,
    render: (b) => dateTimeCell(b.prebid_date, b.prebid_time),
  },
  {
    key: "submission_date",
    label: "Submission",
    group: "Dates",
    kind: "date",
    defaultVisible: true,
    render: (b) => dateTimeCell(b.submission_date, b.submission_time),
  },
  {
    key: "security_mode",
    label: "Security mode",
    group: "Financial",
    kind: "enum",
    defaultVisible: false,
    filterParam: "security_mode",
    render: (b) => b.security_mode || "—",
  },
  {
    key: "security_amount",
    label: "Security amount",
    group: "Financial",
    kind: "money",
    defaultVisible: false,
    filterParam: "security_amount_raw",
    render: (b) => moneyCell(b.security_amount_raw),
  },
  {
    key: "credit_facility",
    label: "Credit facility",
    group: "Financial",
    kind: "money",
    defaultVisible: false,
    filterParam: "credit_facility_raw",
    render: (b) => moneyCell(b.credit_facility_raw),
  },
  {
    key: "bg_issue_date",
    label: "BG issue date",
    group: "Financial",
    kind: "date",
    defaultVisible: false,
    render: (b) => formatDMY(b.bg_issue_date),
  },
  {
    key: "bg_reference",
    label: "BG / reference no.",
    group: "Financial",
    kind: "text",
    defaultVisible: false,
    filterParam: "bg_reference",
    render: (b) => b.bg_reference || "—",
  },
  {
    key: "bg_bank",
    label: "Issuing bank",
    group: "Financial",
    kind: "enum",
    defaultVisible: false,
    filterParam: "bg_bank",
    render: (b) => b.bg_bank || "—",
  },
  {
    key: "bg_expiry_date",
    label: "BG expiry",
    group: "Dates",
    kind: "date",
    defaultVisible: true,
    render: (b) => formatDMY(b.bg_expiry_date),
  },
  {
    key: "submission_status",
    label: "Submission status",
    group: "Status",
    kind: "enum",
    defaultVisible: true,
    filterParam: "submission_status",
    render: (b) => b.submission_status || "—",
  },
  {
    key: "result",
    label: "Result",
    group: "Status",
    kind: "enum",
    defaultVisible: true,
    filterParam: "result",
    render: (b) => b.result || "—",
  },
  {
    key: "remarks",
    label: "Remarks",
    group: "Core",
    kind: "text",
    defaultVisible: false,
    filterParam: "remarks",
    render: (b) => b.remarks || "—",
  },
];

export const DEFAULT_VISIBLE_KEYS = COLUMNS.filter((c) => c.defaultVisible).map((c) => c.key);

export const COLUMN_GROUPS: ColumnGroup[] = ["Core", "New fields", "People", "Dates", "Financial", "Status"];

export const FILTERABLE_ENUM_COLUMNS = COLUMNS.filter((c) => c.kind === "enum" && c.filterParam);
export const FILTERABLE_CONTAINS_COLUMNS = COLUMNS.filter(
  (c) => (c.kind === "text" || c.kind === "list" || c.kind === "money") && c.filterParam
);
