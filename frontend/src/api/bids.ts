import { api } from "./client";

export interface ClientRef {
  id: number;
  name: string;
  canonical_name: string;
}

export interface PersonRef {
  id: number;
  canonical_name: string;
  aliases: string[];
}

export interface TeamRef {
  id: number;
  name: string;
  is_active: boolean;
}

export interface BidListItem {
  id: string;
  serial: number | null;
  reference: string;
  source: "sheet" | "app";
  client: ClientRef;
  description: string;
  cam: PersonRef | null;
  sales_resource: PersonRef | null;
  bid_manager: PersonRef | null;
  team: TeamRef | null;
  engaged_resources: PersonRef[];
  engagement_from: string | null;
  engagement_to: string | null;
  engagement_days: number | null;
  stage: string;
  initiation_mode: string;
  procurement_type: string;
  is_goods: boolean;
  is_works: boolean;
  is_service: boolean;
  tender_id: string;
  initiation_date: string | null;
  published_date: string | null;
  prebid_date: string | null;
  prebid_time: string | null;
  submission_date: string | null;
  submission_time: string | null;
  submission_status: string;
  result: string;
  security_mode: string;
  security_amount_raw: string;
  security_amount: number | null;
  security_currency: string;
  credit_facility_raw: string;
  credit_facility: number | null;
  credit_facility_currency: string;
  bg_issue_date: string | null;
  bg_reference: string;
  bg_bank: string;
  bg_expiry_date: string | null;
  remarks: string;
  missing_from_sheet: boolean;
  is_deleted: boolean;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface BidListParams {
  search?: string;
  page: number;
  page_size: number;
  submission_after: string;
  submission_before: string;
  [filterParam: string]: string | number | undefined;
}

export function fetchBids(params: BidListParams) {
  return api.get<PaginatedResponse<BidListItem>>("/bids/", { params }).then((r) => r.data);
}

export interface DistinctOption {
  value: string;
  label: string;
}

export function fetchDistinctValues(field: string) {
  return api
    .get<{ field: string; options: DistinctOption[] }>("/bids/distinct/", { params: { field } })
    .then((r) => r.data.options);
}
