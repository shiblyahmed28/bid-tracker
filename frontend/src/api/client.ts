import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL;

const ACCESS_KEY = "sbt_access";
const REFRESH_KEY = "sbt_refresh";

// Refresh proactively at 80% of the access token's lifetime so the reactive
// 401-and-retry path below almost never has to run.
const PROACTIVE_REFRESH_FRACTION = 0.8;
// On window focus, treat a token this close to expiry as due for refresh —
// covers a laptop waking from sleep after a scheduled timer was suspended.
const FOCUS_REFRESH_THRESHOLD_MS = 2 * 60 * 1000;

let accessToken: string | null = localStorage.getItem(ACCESS_KEY);
let refreshToken: string | null = localStorage.getItem(REFRESH_KEY);

export interface TokenPair {
  access: string;
  refresh?: string;
}

function decodeExpiryMs(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

let proactiveRefreshTimer: ReturnType<typeof setTimeout> | null = null;

function cancelProactiveRefresh() {
  if (proactiveRefreshTimer) {
    clearTimeout(proactiveRefreshTimer);
    proactiveRefreshTimer = null;
  }
}

function scheduleProactiveRefresh(token: string) {
  cancelProactiveRefresh();
  const expiryMs = decodeExpiryMs(token);
  if (expiryMs === null) return;
  const delay = (expiryMs - Date.now()) * PROACTIVE_REFRESH_FRACTION;
  if (delay <= 0) return;
  proactiveRefreshTimer = setTimeout(() => {
    refreshAccessToken();
  }, delay);
}

export function setTokens(tokens: TokenPair | null) {
  if (tokens === null) {
    accessToken = null;
    refreshToken = null;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    cancelProactiveRefresh();
    return;
  }
  accessToken = tokens.access;
  localStorage.setItem(ACCESS_KEY, tokens.access);
  if (tokens.refresh) {
    refreshToken = tokens.refresh;
    localStorage.setItem(REFRESH_KEY, tokens.refresh);
  }
  scheduleProactiveRefresh(tokens.access);
}

export function getAccessToken() {
  return accessToken;
}

export function getRefreshToken() {
  return refreshToken;
}

// The route guards (ProtectedRoute) are what actually send the user to
// /login — this just tells them a session died so they can clear it. Kept
// as a plain callback rather than an event bus since there's only ever one
// subscriber (AuthProvider).
let onAuthFailure: (() => void) | null = null;
export function setOnAuthFailure(fn: (() => void) | null) {
  onAuthFailure = fn;
}

export const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// Concurrent 401s must not each fire their own refresh call — every request
// that arrives while one is in flight awaits the same promise instead. The
// .catch below runs exactly once when that shared promise settles, no matter
// how many requests are awaiting it, so a failed refresh tears down the
// session and notifies onAuthFailure once — not once per queued request.
let refreshPromise: Promise<string | null> | null = null;

function refreshAccessToken(): Promise<string | null> {
  if (!refreshToken) return Promise.resolve(null);
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${baseURL}/auth/refresh/`, { refresh: refreshToken })
      .then((response) => {
        setTokens({ access: response.data.access, refresh: response.data.refresh });
        return response.data.access as string;
      })
      .catch(() => {
        setTokens(null);
        onAuthFailure?.();
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;

    if (status !== 401 || !original || original._retried) {
      return Promise.reject(error);
    }
    original._retried = true;

    if (!refreshToken) {
      onAuthFailure?.();
      return Promise.reject(error);
    }

    const newAccess = await refreshAccessToken();
    if (newAccess) {
      original.headers.Authorization = `Bearer ${newAccess}`;
      return api(original);
    }

    // refreshAccessToken already cleared the session and notified
    // onAuthFailure once for every request racing this same refresh.
    return Promise.reject(error);
  }
);

if (typeof window !== "undefined") {
  window.addEventListener("focus", () => {
    if (!accessToken) return;
    const expiryMs = decodeExpiryMs(accessToken);
    if (expiryMs !== null && expiryMs - Date.now() < FOCUS_REFRESH_THRESHOLD_MS) {
      refreshAccessToken();
    }
  });

  if (accessToken) scheduleProactiveRefresh(accessToken);
}
