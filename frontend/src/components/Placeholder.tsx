export function Placeholder({ title, description }: { title: string; description: string }) {
  return (
    <div className="card">
      <div className="chead">
        <h2>{title}</h2>
      </div>
      <div className="cbody">
        <p style={{ color: "var(--muted)" }}>{description}</p>
      </div>
    </div>
  );
}
