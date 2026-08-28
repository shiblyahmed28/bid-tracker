import { api } from "./client";

export interface RangeParams {
  from: string;
  to: string;
}

export interface CurrencyTotals {
  BDT: number;
  USD: number;
}

export interface DashboardSummary {
  from: string;
  to: string;
  total: number;
  submitted: number;
  not_submitted: number;
  won: number;
  lost: number;
  pending: number;
  awaiting_result: number;
  win_rate_pct: number | null;
  result_breakdown: Record<string, number>;
  security_locked: CurrencyTotals;
  security_live: { count: number; locked: CurrencyTotals };
}

export interface TrendPoint {
  bucket: string;
  count: number;
  submitted: number;
  not_submitted: number;
}

export interface TrendResponse {
  from: string;
  to: string;
  bucket: "daily" | "monthly" | "quarterly";
  points: TrendPoint[];
}

export type BreakdownBy = "client" | "bid_manager" | "team" | "result";

export interface BreakdownRow {
  label: string;
  count: number;
  won: number;
  lost: number;
}

export interface BreakdownResponse {
  from: string;
  to: string;
  by: BreakdownBy;
  breakdown: BreakdownRow[];
}

export interface BgExposureItem {
  id: string;
  reference: string;
  client: string;
  bg_expiry_date: string;
  bg_bank: string;
  security_amount_raw: string;
  security_amount: number | null;
  security_currency: string;
}

export interface BgExposureResponse {
  days: number;
  as_of: string;
  count: number;
  security_locked: CurrencyTotals;
  items: BgExposureItem[];
}

export interface DeadlineItem {
  id: string;
  reference: string;
  client: string;
  stage: string;
  submission_date: string;
  submission_status: string;
  result: string;
  marker: "submitted" | "open" | "passed";
}

export interface DeadlinesRailResponse {
  mode: "rail";
  items: DeadlineItem[];
  from: string;
  to: string;
}

export interface DeadlinesBucketedResponse {
  mode: "bucketed";
  bucket: "monthly" | "quarterly";
  buckets: { bucket: string; count: number }[];
  from: string;
  to: string;
}

export type DeadlinesResponse = DeadlinesRailResponse | DeadlinesBucketedResponse;

export interface BidSummary {
  id: string;
  reference: string;
  submission_date: string | null;
}

export function fetchSummary(params: RangeParams) {
  return api.get<DashboardSummary>("/dashboard/summary/", { params }).then((r) => r.data);
}

/** Classic view's own summary endpoint (§17) — same shape as /dashboard/summary/
 * today, called separately (not aliased to fetchSummary) so the two pages stay
 * independent if the backend ever diverges them. */
export function fetchClassicSummary(params: RangeParams) {
  return api.get<DashboardSummary>("/dashboard/classic/", { params }).then((r) => r.data);
}

export function fetchTrend(params: RangeParams) {
  return api.get<TrendResponse>("/dashboard/trend/", { params }).then((r) => r.data);
}

export function fetchBreakdown(params: RangeParams & { by: BreakdownBy }) {
  return api.get<BreakdownResponse>("/dashboard/breakdown/", { params }).then((r) => r.data);
}

export function fetchBgExposure(params: RangeParams & { days?: number }) {
  return api.get<BgExposureResponse>("/dashboard/bg-exposure/", { params }).then((r) => r.data);
}

export function fetchDeadlines(params: RangeParams) {
  return api.get<DeadlinesResponse>("/dashboard/deadlines/", { params }).then((r) => r.data);
}

/** For the "Awaiting result" KPI footer — the oldest still-pending bid's
 * submission date. Not worth a dedicated summary field for one footer line. */
export function fetchOldestPending(params: RangeParams) {
  return api
    .get<{ results: BidSummary[] }>("/bids/", {
      params: {
        result: "PENDING",
        submission_after: params.from,
        submission_before: params.to,
        ordering: "submission_date",
        page_size: 1,
      },
    })
    .then((r) => r.data.results[0]?.submission_date ?? null);
}
