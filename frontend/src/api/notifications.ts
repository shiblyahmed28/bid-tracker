import { api } from "./client";
import type { PaginatedResponse } from "./bids";

export type NotificationKind = "new_bid" | "field_change" | "deadline";

export interface NotificationItem {
  id: number;
  kind: NotificationKind;
  title: string;
  body: string;
  bid: string | null;
  bid_reference: string | null;
  read: boolean;
  created_at: string;
}

export function fetchNotifications(page = 1) {
  return api.get<PaginatedResponse<NotificationItem>>("/notifications/", { params: { page } }).then((r) => r.data);
}

export function markNotificationRead(id: number) {
  return api.post(`/notifications/${id}/read/`);
}

export function markAllNotificationsRead() {
  return api.post<{ updated: number }>("/notifications/mark-all-read/").then((r) => r.data);
}

export interface NotificationSettings {
  notifications_muted: boolean;
  email_digest: boolean;
  email_deadline: boolean;
  email_newbid: boolean;
  fields: Record<string, boolean>;
  field_labels: Record<string, string>;
}

export function fetchNotificationSettings() {
  return api.get<NotificationSettings>("/notifications/settings/").then((r) => r.data);
}

export interface NotificationSettingsPatch {
  notifications_muted?: boolean;
  email_digest?: boolean;
  email_deadline?: boolean;
  email_newbid?: boolean;
  fields?: Record<string, boolean>;
}

export function updateNotificationSettings(payload: NotificationSettingsPatch) {
  return api.patch<NotificationSettings>("/notifications/settings/", payload).then((r) => r.data);
}

// ---------- Sent email log (§Phase 21 item 4, admin-only) ----------

export type SentEmailKind =
  | "new_bid"
  | "deadline"
  | "policy_event"
  | "digest"
  | "welcome_engagement"
  | "password_reset";

export interface SentEmailItem {
  id: number;
  to_email: string;
  subject: string;
  kind: SentEmailKind;
  bid: string | null;
  bid_reference: string | null;
  success: boolean;
  error: string;
  created_at: string;
}

export interface SentEmailFilters {
  kind?: SentEmailKind | "";
  success?: "true" | "false" | "";
  recipient?: string;
  page?: number;
  page_size?: number;
}

export function fetchSentEmails(filters: SentEmailFilters) {
  return api.get<PaginatedResponse<SentEmailItem>>("/notifications/sent-log/", { params: filters }).then((r) => r.data);
}
