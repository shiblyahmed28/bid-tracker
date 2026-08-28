import type { Role } from "../auth/AuthContext";
import { api } from "./client";

// ---------- Choice lists ----------

export interface ChoiceListItem {
  id: number;
  key: string;
  label: string;
  description: string;
  is_locked: boolean;
  values_count: number;
}

export interface ChoiceValueItem {
  id: number;
  list: number;
  value: string;
  label: string;
  sort_order: number;
  is_active: boolean;
  is_default: boolean;
  created_by_sync: boolean;
  created_by: number | null;
  created_by_email: string | null;
  created_at: string;
  usage_count: number;
}

export function fetchChoiceLists() {
  return api.get<ChoiceListItem[]>("/settings/choice-lists/").then((r) => r.data);
}

export function fetchChoiceValues(listKey: string) {
  return api.get<ChoiceValueItem[]>(`/settings/choice-lists/${listKey}/values/`).then((r) => r.data);
}

export function createChoiceValue(listKey: string, payload: { value: string; label: string }) {
  return api.post<ChoiceValueItem>(`/settings/choice-lists/${listKey}/values/`, payload).then((r) => r.data);
}

export function updateChoiceValue(
  listKey: string,
  id: number,
  payload: Partial<Pick<ChoiceValueItem, "label" | "is_active" | "is_default" | "sort_order">>
) {
  return api.patch<ChoiceValueItem>(`/settings/choice-lists/${listKey}/values/${id}/`, payload).then((r) => r.data);
}

export function renameChoiceValue(listKey: string, id: number, newValue: string, newLabel: string) {
  return api
    .post<{ updated_bids: number; value: ChoiceValueItem }>(
      `/settings/choice-lists/${listKey}/values/${id}/rename/`,
      { new_value: newValue, new_label: newLabel }
    )
    .then((r) => r.data);
}

export function reorderChoiceValues(listKey: string, orderedIds: number[]) {
  return api.post(`/settings/choice-lists/${listKey}/reorder/`, { order: orderedIds });
}

// ---------- Reference data (Clients / People / Teams) ----------

export interface SettingsClient {
  id: number;
  name: string;
  canonical_name: string;
}

export interface SettingsPerson {
  id: number;
  canonical_name: string;
  aliases: string[];
}

export interface SettingsTeam {
  id: number;
  name: string;
  is_active: boolean;
}

export function fetchSettingsClients() {
  return api.get<SettingsClient[]>("/settings/clients/").then((r) => r.data);
}
export function updateSettingsClient(id: number, payload: Partial<SettingsClient>) {
  return api.patch<SettingsClient>(`/settings/clients/${id}/`, payload).then((r) => r.data);
}

export function fetchSettingsPeople() {
  return api.get<SettingsPerson[]>("/settings/people/").then((r) => r.data);
}
export function updateSettingsPerson(id: number, payload: Partial<SettingsPerson>) {
  return api.patch<SettingsPerson>(`/settings/people/${id}/`, payload).then((r) => r.data);
}

export function fetchSettingsTeams() {
  return api.get<SettingsTeam[]>("/settings/teams/").then((r) => r.data);
}
export function updateSettingsTeam(id: number, payload: Partial<SettingsTeam>) {
  return api.patch<SettingsTeam>(`/settings/teams/${id}/`, payload).then((r) => r.data);
}

// ---------- Capabilities ----------

export interface CapabilitiesReference {
  capabilities: string[];
  role_defaults: Record<Role, string[]>;
}

export function fetchCapabilitiesReference() {
  return api.get<CapabilitiesReference>("/settings/capabilities/").then((r) => r.data);
}

export type CapabilitySource = "role_default" | "override";

export interface EffectiveCapability {
  capability: string;
  granted: boolean;
  source: CapabilitySource;
}

export interface UserCapabilitiesResponse {
  user: number;
  role: Role;
  effective: EffectiveCapability[];
  overrides: { capability: string; granted: boolean; granted_by_email: string | null; granted_at: string }[];
}

export function fetchUserCapabilities(userId: number) {
  return api.get<UserCapabilitiesResponse>(`/settings/users/${userId}/capabilities/`).then((r) => r.data);
}

export function setUserCapability(userId: number, capability: string, granted: boolean) {
  return api
    .post<UserCapabilitiesResponse>(`/settings/users/${userId}/capabilities/`, { capability, granted })
    .then((r) => r.data);
}

export function clearUserCapability(userId: number, capability: string) {
  return api
    .delete<UserCapabilitiesResponse>(`/settings/users/${userId}/capabilities/`, { params: { capability } })
    .then((r) => r.data);
}

// ---------- Notification policy ----------

export interface NotificationPolicyItem {
  id: number;
  event_key: string;
  label: string;
  default_in_app: boolean;
  default_email: boolean;
  applies_to_roles: Role[];
  is_active: boolean;
}

export function fetchNotificationPolicies() {
  return api.get<NotificationPolicyItem[]>("/settings/notification-policies/").then((r) => r.data);
}

export function updateNotificationPolicy(id: number, payload: Partial<NotificationPolicyItem>) {
  return api.patch<NotificationPolicyItem>(`/settings/notification-policies/${id}/`, payload).then((r) => r.data);
}

// ---------- Deadline reminder rules ----------

export interface DeadlineReminderRuleItem {
  id: number;
  days_before: number;
  is_active: boolean;
  applies_to_roles: Role[];
  users: number[];
}

export function fetchDeadlineRules() {
  return api.get<DeadlineReminderRuleItem[]>("/settings/deadline-rules/").then((r) => r.data);
}

export function updateDeadlineRule(id: number, payload: Partial<DeadlineReminderRuleItem>) {
  return api.patch<DeadlineReminderRuleItem>(`/settings/deadline-rules/${id}/`, payload).then((r) => r.data);
}
