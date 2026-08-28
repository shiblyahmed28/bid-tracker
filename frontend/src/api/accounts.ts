import type { Role } from "../auth/AuthContext";
import { api } from "./client";

export interface ProfileUpdatePayload {
  full_name?: string;
  email?: string;
  phone?: string;
}

export function updateProfile(payload: ProfileUpdatePayload) {
  return api.patch("/auth/profile/", payload).then((r) => r.data);
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export function changePassword(payload: ChangePasswordPayload) {
  return api.post<{ revoked_sessions: number }>("/auth/change-password/", payload).then((r) => r.data);
}

export type DeviceType = "desktop" | "mobile" | "tablet" | "unknown";

export interface SessionItem {
  id: number;
  ip: string | null;
  user_agent: string;
  device_type: DeviceType;
  device_brand: string;
  os: string;
  browser: string;
  created_at: string;
  last_seen_at: string;
  revoked_at: string | null;
  is_active: boolean;
  is_current: boolean;
}

function unwrap<T>(data: T[] | { results: T[] }): T[] {
  return Array.isArray(data) ? data : data.results;
}

export function fetchOwnSessions() {
  return api
    .get<SessionItem[] | { results: SessionItem[] }>("/auth/sessions/")
    .then((r) => unwrap(r.data));
}

export function fetchUserSessions(userId: number) {
  return api
    .get<SessionItem[] | { results: SessionItem[] }>(`/users/${userId}/sessions/`)
    .then((r) => unwrap(r.data));
}

export function revokeSession(id: number) {
  return api.post(`/auth/sessions/${id}/revoke/`);
}

export function revokeOtherSessions() {
  return api.post<{ revoked: number }>("/auth/sessions/revoke-others/").then((r) => r.data);
}

export interface AdminUser {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  role: Role;
  is_active: boolean;
  must_change_password: boolean;
  date_joined: string;
}

export function fetchUsers() {
  return api.get<AdminUser[] | { results: AdminUser[] }>("/users/").then((r) => unwrap(r.data));
}

export interface AdminResetPasswordPayload {
  new_password: string;
  confirm_password: string;
  force_change: boolean;
  email_user: boolean;
  revoke_sessions: boolean;
}

export function adminResetPassword(userId: number, payload: AdminResetPasswordPayload) {
  return api
    .post<{ force_change: boolean; emailed: boolean; revoked_sessions: number }>(
      `/users/${userId}/reset-password/`,
      payload
    )
    .then((r) => r.data);
}
