export function Skeleton({ height = 16, width = "100%" }: { height?: number | string; width?: number | string }) {
  return <div className="skel" style={{ height, width }} />;
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="empty">
      <h3>Nothing here</h3>
      <p>{message}. Widen the date range or clear your filters.</p>
    </div>
  );
}
