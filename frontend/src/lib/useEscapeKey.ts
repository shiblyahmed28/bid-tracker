import { useEffect } from "react";

/** Escape closes the drawer and any modal (§19's responsive requirement) —
 * modals built in later phases should reuse this rather than each rolling
 * their own listener. */
export function useEscapeKey(onEscape: () => void, enabled = true) {
  useEffect(() => {
    if (!enabled) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onEscape();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onEscape, enabled]);
}
