/** Fired once a manual "Fetch data" sync run completes (Topbar) — every
 * range-driven panel and the bid register subscribe so they refetch instead
 * of showing stale data until the next full page load. Mirrors
 * notificationBus's pub/sub shape. */
type Listener = () => void;
const listeners = new Set<Listener>();

export function subscribeDataSynced(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function notifyDataSynced() {
  listeners.forEach((listener) => listener());
}
