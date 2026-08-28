import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { api, getAccessToken, getRefreshToken, setOnAuthFailure, setTokens } from "../api/client";

export type Role = "admin" | "editor" | "viewer";

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  must_change_password: boolean;
  notifications_muted: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  isInitializing: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  const clearLocalSession = useCallback(() => {
    setTokens(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setOnAuthFailure(clearLocalSession);
    return () => setOnAuthFailure(null);
  }, [clearLocalSession]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (!getAccessToken() && !getRefreshToken()) {
        setIsInitializing(false);
        return;
      }
      try {
        const response = await api.get<AuthUser>("/auth/me/");
        if (!cancelled) setUser(response.data);
      } catch {
        if (!cancelled) clearLocalSession();
      } finally {
        if (!cancelled) setIsInitializing(false);
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [clearLocalSession]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api.post("/auth/login/", { email, password });
    setTokens({ access: response.data.access, refresh: response.data.refresh });
    const me = await api.get<AuthUser>("/auth/me/");
    setUser(me.data);
  }, []);

  const logout = useCallback(() => {
    const refresh = getRefreshToken();
    if (refresh) {
      api.post("/auth/logout/", { refresh }).catch(() => {
        // The session is being torn down locally regardless — this is a
        // best-effort courtesy call to revoke the refresh token server-side.
      });
    }
    clearLocalSession();
  }, [clearLocalSession]);

  return (
    <AuthContext.Provider value={{ user, isInitializing, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
