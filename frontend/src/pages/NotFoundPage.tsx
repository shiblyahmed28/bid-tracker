import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="card">
      <div className="cbody" style={{ textAlign: "center", padding: "48px 24px" }}>
        <h2 style={{ fontSize: 22, marginBottom: 8 }}>Page not found</h2>
        <p className="hint" style={{ marginBottom: 18 }}>
          That page doesn't exist, or you don't have a link to it anymore.
        </p>
        <Link className="btn btn-p" to="/dashboard">
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
