import { type FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

const EMAIL_DOMAIN_RE = /^[^@\s]+@spectrum-bd\.com$/i;

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [domainError, setDomainError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    const from = (location.state as { from?: Location })?.from;
    return <Navigate to={from?.pathname ?? "/dashboard"} replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setServerError(null);

    // Client-side check for feedback only — the server is the real gate (§14).
    if (!EMAIL_DOMAIN_RE.test(email.trim())) {
      setDomainError("Use your @spectrum-bd.com address.");
      return;
    }
    setDomainError(null);

    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate("/dashboard", { replace: true });
    } catch {
      setServerError("Incorrect email or password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-mark">
          <img src="/logo.png" alt="Spectrum" />
          <b>Spectrum</b>
        </div>
        <p className="login-sub">Bid Tracker — sign in to continue</p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setDomainError(null);
              }}
              required
            />
            {domainError && <p className="err">{domainError}</p>}
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {serverError && <p className="err" style={{ marginBottom: 13 }}>{serverError}</p>}

          <button type="submit" className="btn btn-p btn-full" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="login-hint">
          Internal tool for Spectrum Engineering Consortium (Pvt.) Ltd. Only{" "}
          <b>@spectrum-bd.com</b> addresses are accepted.
        </p>
      </div>
    </div>
  );
}
