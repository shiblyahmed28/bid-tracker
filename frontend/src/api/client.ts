import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL;

const ACCESS_KEY = "sbt_access";
const REFRESH_KEY = "sbt_refresh";

let accessToken: string | null = localStorage.getItem(ACCESS_KEY);
let refreshToken: string | null = localStorage.getItem(REFRESH_KEY);

export interface TokenPair {
  access: string;
  refresh?: string;
}

export function setTokens(tokens: TokenPair | null) {
  if (tokens === null) {
    accessToken = null;
    refreshToken = null;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    return;
  }
  accessToken = tokens.access;
  localStorage.setItem(ACCESS_KEY, tokens.access);
  if (tokens.refresh) {
    refreshToken = tokens.refresh;
    localStorage.setItem(REFRESH_KEY, tokens.refresh);
  }
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
// that arrives while one is in flight awaits the same promise instead.
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

    if (status === 401 && original && !original._retried && refreshToken) {
      original._retried = true;
      const newAccess = await refreshAccessToken();
      if (newAccess) {
        original.headers.Authorization = `Bearer ${newAccess}`;
        return api(original);
      }
    }

    if (status === 401) {
      onAuthFailure?.();
    }

    return Promise.reject(error);
  }
);
