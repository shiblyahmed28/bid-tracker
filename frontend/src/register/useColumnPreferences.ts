import { useEffect, useState } from "react";

import { useAuth } from "../auth/AuthContext";
import { COLUMNS, DEFAULT_VISIBLE_KEYS } from "./columns";

const STORAGE_PREFIX = "sbt_register_columns_";

/** Persisted in localStorage, keyed per user id — the column picker's
 * "your call" persistence choice (§13). No backend model/migration needed,
 * and it's genuinely per-browser-per-user since the key includes the id. */
function storageKey(userId: number) {
  return `${STORAGE_PREFIX}${userId}`;
}

function loadStored(userId: number): string[] | null {
  try {
    const raw = localStorage.getItem(storageKey(userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    const validKeys = new Set(COLUMNS.map((c) => c.key));
    const filtered = parsed.filter((k): k is string => typeof k === "string" && validKeys.has(k));
    return filtered.length ? filtered : null;
  } catch {
    return null;
  }
}

export function useColumnPreferences() {
  const { user } = useAuth();
  const [visibleKeys, setVisibleKeys] = useState<string[]>(
    () => (user && loadStored(user.id)) ?? DEFAULT_VISIBLE_KEYS
  );

  useEffect(() => {
    if (!user) return;
    setVisibleKeys(loadStored(user.id) ?? DEFAULT_VISIBLE_KEYS);
  }, [user]);

  function persist(next: string[]) {
    setVisibleKeys(next);
    if (!user) return;
    try {
      localStorage.setItem(storageKey(user.id), JSON.stringify(next));
    } catch {
      // Quota or private-mode failure — the in-memory selection still works
      // for the rest of this session either way.
    }
  }

  function toggleColumn(key: string) {
    const next = visibleKeys.includes(key) ? visibleKeys.filter((k) => k !== key) : [...visibleKeys, key];
    persist(next.length ? next : ["client"]);
  }

  function selectAll() {
    persist(COLUMNS.map((c) => c.key));
  }

  function resetToDefault() {
    persist(DEFAULT_VISIBLE_KEYS);
  }

  return { visibleKeys, toggleColumn, selectAll, resetToDefault };
}
