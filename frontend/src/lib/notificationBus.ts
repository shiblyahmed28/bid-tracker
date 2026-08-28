/** The bell dropdown and the full Notifications page each hold their own
 * copy of the notification list — this just tells one to refetch when the
 * other changes read-state, so neither goes stale while both are visible. */
type Listener = () => void;
const listeners = new Set<Listener>();

export function subscribeNotificationsChanged(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function notifyNotificationsChanged() {
  listeners.forEach((listener) => listener());
}
