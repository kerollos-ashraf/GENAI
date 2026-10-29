import { Component, type ErrorInfo, type ReactNode } from "react";
import { BrandMark } from "./Header";

interface State {
  error: Error | null;
}

/** Last line of defence: a rendering bug shows a way back instead of a blank page. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  override state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("UI crashed", error, info.componentStack);
  }

  override render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="crash" role="alert">
        <BrandMark />
        <h1>Something went wrong on this page</h1>
        <p>Your conversation couldn't be shown. Reload to start again; nothing was sent.</p>
        <button
          className="button"
          onClick={() => {
            window.location.reload();
          }}
        >
          Reload
        </button>
      </main>
    );
  }
}
