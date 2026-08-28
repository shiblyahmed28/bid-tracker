import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("Unhandled error in page:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="card">
          <div className="cbody" style={{ textAlign: "center", padding: "48px 24px" }}>
            <h2 style={{ fontSize: 22, marginBottom: 8 }}>Something went wrong</h2>
            <p className="hint" style={{ marginBottom: 18 }}>
              This page hit an unexpected error. Reloading usually fixes it.
            </p>
            <button className="btn btn-p" onClick={() => window.location.reload()}>
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
