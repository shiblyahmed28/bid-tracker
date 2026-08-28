import { api } from "./client";
import type { PaginatedResponse } from "./bids";
import { triggerBlobDownload } from "./exports";

export interface AuditEntryItem {
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

export interface AuditFilters {
  actor?: number;
  action?: string;
  created_after?: string;
  created_before?: string;
  page?: number;
  page_size?: number;
}

export function fetchAuditEntries(filters: AuditFilters) {
  return api.get<PaginatedResponse<AuditEntryItem>>("/audit/", { params: filters }).then((r) => r.data);
}

export async function downloadAuditCsv(filters: AuditFilters): Promise<void> {
  const response = await api.get("/audit/export/", { params: filters, responseType: "blob" });
  triggerBlobDownload(response.data as Blob, "audit-log.csv");
}
