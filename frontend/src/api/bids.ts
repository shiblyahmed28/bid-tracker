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

export interface ConflictSummary {
  id: number;
  field: string;
  sheet_value: string;
  local_value: string;
  local_editor: string | null;
  local_edited_at: string;
  created_at: string;
}

export interface BidDetail extends BidListItem {
  uid: string | null;
  sheet_row: number | null;
  locally_overridden: string[];
  conflicts: ConflictSummary[];
  has_unresolved_conflicts: boolean;
  created_by: number | null;
  created_by_email: string | null;
  updated_by: number | null;
  updated_by_email: string | null;
  created_at: string;
  updated_at: string;
}

/** Matches BidWriteSerializer (§17) — client/cam/sales_resource/bid_manager
 * are free text resolved server-side like the sync pipeline; team and
 * engaged_resources are real ids since they're app-native curated lists (§7). */
export interface BidWritePayload {
  client_name: string;
  description: string;
  cam_name?: string;
  sales_resource_name?: string;
  bid_manager_name?: string;
  team?: number | null;
  engaged_resources?: number[];
  engagement_from?: string | null;
  engagement_to?: string | null;
  stage?: string;
  initiation_mode?: string;
  procurement_type?: string;
  is_goods?: boolean;
  is_works?: boolean;
  is_service?: boolean;
  tender_id?: string;
  initiation_date?: string | null;
  published_date?: string | null;
  prebid_date?: string | null;
  prebid_time?: string | null;
  submission_date: string;
  submission_time?: string | null;
  submission_status?: string;
  result?: string;
  security_mode?: string;
  security_amount_raw?: string;
  security_amount?: number | null;
  security_currency?: string;
  credit_facility_raw?: string;
  credit_facility?: number | null;
  credit_facility_currency?: string;
  bg_issue_date?: string | null;
  bg_reference?: string;
  bg_bank?: string;
  bg_expiry_date?: string | null;
  remarks?: string;
}

export function fetchBid(id: string) {
  return api.get<BidDetail>(`/bids/${id}/`).then((r) => r.data);
}

export function createBid(payload: Partial<BidWritePayload>) {
  return api.post<BidDetail>("/bids/", payload).then((r) => r.data);
}

export function updateBid(id: string, payload: Partial<BidWritePayload>) {
  return api.patch<BidDetail>(`/bids/${id}/`, payload).then((r) => r.data);
}

export function deleteBid(id: string) {
  return api.delete(`/bids/${id}/`);
}

export interface HistoryEntry {
  id: number;
  actor: number | null;
  actor_email: string | null;
  actor_label: string;
  action: string;
  bid: string | null;
  bid_reference: string | null;
  field: string;
  old_value: string | null;
  new_value: string | null;
  ip: string | null;
  user_agent: string;
  created_at: string;
}

export function fetchBidHistory(id: string) {
  return api.get<PaginatedResponse<HistoryEntry>>(`/bids/${id}/history/`).then((r) => r.data);
}

export function fetchPeople() {
  return api.get<PersonRef[]>("/people/").then((r) => r.data);
}

export function resolveConflict(conflictId: number, choose: "sheet" | "local") {
  return api.post(`/sync/conflicts/${conflictId}/resolve/`, { choose }).then((r) => r.data);
}
