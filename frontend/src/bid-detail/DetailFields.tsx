import type { BidDetail } from "../api/bids";
import { formatDMY } from "../lib/dateUtils";

function moneyDisplay(raw: string, amount: number | null, currency: string): string {
  if (!raw) return "—";
  if (amount === null) return raw;
  return `${raw} (parsed: ${currency} ${amount.toLocaleString("en-US")})`;
}

function dateTimeDisplay(date: string | null, time: string | null): string {
  if (!date) return "—";
  return time ? `${formatDMY(date)}, ${time.slice(0, 5)}` : formatDMY(date);
}

function deliveryType(bid: BidDetail): string {
  return [bid.is_goods && "Goods", bid.is_works && "Works", bid.is_service && "Service"].filter(Boolean).join(", ") || "—";
}

/** Every field, in a definition list (§11) — including the _raw money
 * strings shown exactly as typed alongside their parsed interpretation. */
export function DetailFields({ bid }: { bid: BidDetail }) {
  return (
    <dl className="dl">
      <dt>Reference</dt>
      <dd className="num">{bid.reference}</dd>

      <dt>Serial (SL)</dt>
      <dd>
        <span className="num">{bid.serial ?? "—"}</span>{" "}
        <span className="hint">— a display position, shifts as records are added or removed</span>
      </dd>

      <dt>Source</dt>
      <dd>{bid.source === "sheet" ? "Google Sheet" : "Created in app"}</dd>

      <dt>Client</dt>
      <dd>{bid.client.name}</dd>

      <dt>Description</dt>
      <dd>{bid.description || "—"}</dd>

      <dt>Team</dt>
      <dd>{bid.team?.name ?? "—"}</dd>

      <dt>Stage</dt>
      <dd>{bid.stage || "—"}</dd>

      <dt>Procurement type</dt>
      <dd>{bid.procurement_type || "—"}</dd>

      <dt>Initiation mode</dt>
      <dd>{bid.initiation_mode || "—"}</dd>

      <dt>Delivery type</dt>
      <dd>{deliveryType(bid)}</dd>

      <dt>Tender ID</dt>
      <dd>{bid.tender_id || "—"}</dd>

      <dt>CAM</dt>
      <dd>{bid.cam?.canonical_name ?? "—"}</dd>

      <dt>Sales resource</dt>
      <dd>{bid.sales_resource?.canonical_name ?? "—"}</dd>

      <dt>Bid manager</dt>
      <dd>{bid.bid_manager?.canonical_name ?? "—"}</dd>

      <dt>Engaged resources</dt>
      <dd>
        {bid.engaged_resources.length
          ? `${bid.engaged_resources.map((p) => p.canonical_name).join(", ")} (${bid.engaged_resources.length})`
          : "—"}
      </dd>

      <dt>Engagement period</dt>
      <dd>
        {bid.engagement_from
          ? `${formatDMY(bid.engagement_from)} → ${formatDMY(bid.engagement_to)} (${bid.engagement_days}d)`
          : "—"}
      </dd>

      <dt>Initiation date</dt>
      <dd>{formatDMY(bid.initiation_date)}</dd>

      <dt>Published</dt>
      <dd>{formatDMY(bid.published_date)}</dd>

      <dt>Pre-bid</dt>
      <dd>{dateTimeDisplay(bid.prebid_date, bid.prebid_time)}</dd>

      <dt>Submission</dt>
      <dd>{dateTimeDisplay(bid.submission_date, bid.submission_time)}</dd>

      <dt>Submission status</dt>
      <dd>{bid.submission_status || "—"}</dd>

      <dt>Result</dt>
      <dd>{bid.result || "—"}</dd>

      <dt>Security mode</dt>
      <dd>{bid.security_mode || "—"}</dd>

      <dt>Security amount</dt>
      <dd>{moneyDisplay(bid.security_amount_raw, bid.security_amount, bid.security_currency)}</dd>

      <dt>Credit facility</dt>
      <dd>{moneyDisplay(bid.credit_facility_raw, bid.credit_facility, bid.credit_facility_currency)}</dd>

      <dt>BG issue date</dt>
      <dd>{formatDMY(bid.bg_issue_date)}</dd>

      <dt>BG / reference no.</dt>
      <dd>{bid.bg_reference || "—"}</dd>

      <dt>Issuing bank</dt>
      <dd>{bid.bg_bank || "—"}</dd>

      <dt>BG expiry</dt>
      <dd>{formatDMY(bid.bg_expiry_date)}</dd>

      <dt>Remarks</dt>
      <dd>{bid.remarks || "—"}</dd>

      <dt>Missing from sheet</dt>
      <dd>{bid.missing_from_sheet ? "Yes — flagged for review" : "No"}</dd>
    </dl>
  );
}
