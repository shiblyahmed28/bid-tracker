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

export type PersonType = "internal" | "external";

export interface SettingsPerson {
  id: number;
  canonical_name: string;
  aliases: string[];
  email: string | null;
  person_type: PersonType;
  organization: string;
  phone: string;
  is_active: boolean;
  user: number | null;
  user_email: string | null;
  user_full_name: string | null;
  usage_count: number;
}

export interface SettingsTeam {
  id: number;
  name: string;
  is_active: boolean;
}

export function fetchSettingsClients() {
  return api.get<SettingsClient[]>("/settings/clients/").then((r) => r.data);
}
export function createSettingsClient(payload: { name: string }) {
  return api.post<SettingsClient>("/settings/clients/", payload).then((r) => r.data);
}
export function updateSettingsClient(id: number, payload: Partial<SettingsClient>) {
  return api.patch<SettingsClient>(`/settings/clients/${id}/`, payload).then((r) => r.data);
}

export interface PersonFilters {
  person_type?: PersonType;
  is_active?: boolean;
}

export function fetchSettingsPeople(filters: PersonFilters = {}) {
  return api.get<SettingsPerson[]>("/settings/people/", { params: filters }).then((r) => r.data);
}
export function createSettingsPerson(payload: { canonical_name: string }) {
  return api.post<SettingsPerson>("/settings/people/", payload).then((r) => r.data);
}
export function updateSettingsPerson(id: number, payload: Partial<SettingsPerson>) {
  return api.patch<SettingsPerson>(`/settings/people/${id}/`, payload).then((r) => r.data);
}

// ---------- Engaged resources: dedup/merge, engagement history, welcome email (§Phase 20) ----------

export interface PersonDuplicateGroup {
  people: SettingsPerson[];
}

export function fetchPersonDuplicates() {
  return api.get<PersonDuplicateGroup[]>("/settings/people/duplicates/").then((r) => r.data);
}

export interface MergePersonsResult {
  survivor: SettingsPerson;
  engagements_reassigned: number;
  engagements_skipped: number;
  cam_reassigned: number;
  sales_resource_reassigned: number;
  bid_manager_reassigned: number;
}

export function mergePersons(survivorId: number, duplicateId: number) {
  return api
    .post<MergePersonsResult>(`/settings/people/${survivorId}/merge/`, { duplicate_id: duplicateId })
    .then((r) => r.data);
}

export interface EngagementBidSummary {
  id: string;
  reference: string;
  client_name: string;
  submission_date: string | null;
  stage: string;
  result: string;
}

export interface PersonEngagement {
  id: number;
  bid: EngagementBidSummary;
  engaged_from: string | null;
  engaged_to: string | null;
  days: number;
  convenience_bill: number;
  note: string;
  welcome_email_sent_at: string | null;
}

export interface PersonEngagementHistory {
  person: SettingsPerson;
  engagements: PersonEngagement[];
  totals: { days: number; convenience_bill: number };
}

export function fetchPersonEngagements(personId: number) {
  return api.get<PersonEngagementHistory>(`/settings/people/${personId}/engagements/`).then((r) => r.data);
}

export interface WelcomeEmailSettingsData {
  enabled: boolean;
  updated_by_email: string | null;
  updated_at: string;
}

export function fetchWelcomeEmailSettings() {
  return api.get<WelcomeEmailSettingsData>("/settings/welcome-email/").then((r) => r.data);
}

export function updateWelcomeEmailSettings(enabled: boolean) {
  return api.patch<WelcomeEmailSettingsData>("/settings/welcome-email/", { enabled }).then((r) => r.data);
}

export function sendWelcomeEmail(engagementId: number) {
  return api.post<PersonEngagement>(`/settings/engagements/${engagementId}/welcome-email/`).then((r) => r.data);
}

export function fetchSettingsTeams() {
  return api.get<SettingsTeam[]>("/settings/teams/").then((r) => r.data);
}
export function createSettingsTeam(payload: { name: string }) {
  return api.post<SettingsTeam>("/settings/teams/", payload).then((r) => r.data);
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
