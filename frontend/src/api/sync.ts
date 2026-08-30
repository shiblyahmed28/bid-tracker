import { api } from "./client";
import type { PaginatedResponse } from "./bids";

export interface SyncRunItem {
  id: number;
  trigger: "scheduled" | "manual";
  actor: number | null;
  actor_email: string | null;
  status: "running" | "success" | "failed";
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  rows_read: number;
  rows_created: number;
  rows_updated: number;
  rows_conflicted: number;
  rows_quarantined: number;
}

export interface QuarantineRowItem {
  id: number;
  sync_run: number;
  sheet_row: number | null;
  raw_data: { row?: unknown };
  reason: string;
  created_at: string;
}

export interface SyncConflictItem {
  id: number;
  sync_run: number;
  bid: string;
  bid_reference: string;
  field: string;
  sheet_value: string | null;
  local_value: string | null;
  local_editor: number | null;
  local_editor_email: string | null;
  local_edited_at: string | null;
  resolved: boolean;
  resolution: "sheet" | "local" | "";
  resolved_by: number | null;
  resolved_by_email: string | null;
  resolved_at: string | null;
  created_at: string;
}

export function fetchSyncRuns(page = 1, pageSize = 10) {
  return api
    .get<PaginatedResponse<SyncRunItem>>("/sync/runs/", { params: { page, page_size: pageSize } })
    .then((r) => r.data);
}

export function fetchQuarantineRows(page = 1, pageSize = 10) {
  return api
    .get<PaginatedResponse<QuarantineRowItem>>("/sync/quarantine/", { params: { page, page_size: pageSize } })
    .then((r) => r.data);
}

export function triggerSyncRun() {
  return api.post<SyncRunItem>("/sync/run/").then((r) => r.data);
}

export interface PendingSheetAppendItem {
  id: string;
  reference: string;
  client_name: string;
  sheet_append_error: string;
  created_at: string;
}

export function fetchPendingSheetAppends(page = 1, pageSize = 10) {
  return api
    .get<PaginatedResponse<PendingSheetAppendItem>>("/sync/pending-appends/", { params: { page, page_size: pageSize } })
    .then((r) => r.data);
}

export interface SyncResetResult {
  deleted: number;
  sync_run: SyncRunItem;
}

/** POST /sync/reset/ — admin-only danger-zone action: deletes every bid
 * (app-created and sheet-sourced alike) and resyncs fresh from the sheet. */
export function resetBidData() {
  return api.post<SyncResetResult>("/sync/reset/", { confirm: true }).then((r) => r.data);
}
