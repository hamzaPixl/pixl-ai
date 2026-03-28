import { createRootRoute, Outlet } from '@tanstack/react-router';
import { Component, useEffect, useRef, type ReactNode, type ErrorInfo } from 'react';
import { useAuthStore } from '@/stores/auth';
import { startTokenRefresh, stopTokenRefresh } from '@/lib/token-refresh';
import { Button } from '@/components/ui/button';
import { AlertTriangle } from 'lucide-react';

// ─── Root Error Boundary ─────────────────────────────────────────────

interface RootErrorBoundaryProps { children: ReactNode }
interface RootErrorBoundaryState { error: Error | null }

class RootErrorBoundary extends Component<RootErrorBoundaryProps, RootErrorBoundaryState> {
  state: RootErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[RootErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="max-w-md text-center space-y-4 p-6">
            <AlertTriangle className="h-10 w-10 text-destructive mx-auto" />
            <h1 className="text-lg font-semibold">Something went wrong</h1>
            <p className="text-sm text-muted-foreground">
              An unexpected error occurred. You can try reloading the page or going back.
            </p>
            <p className="text-xs text-muted-foreground font-mono bg-muted p-2 rounded">
              {this.state.error.message}
            </p>
            <div className="flex items-center justify-center gap-3">
              <Button variant="outline" onClick={() => this.setState({ error: null })}>
                Try again
              </Button>
              <Button onClick={() => window.location.reload()}>
                Reload page
              </Button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── Root Route ──────────────────────────────────────────────────────

export const Route = createRootRoute({
  component: RootComponent,
});

function RootComponent() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const tokenIat = useAuthStore((s) => s.tokenIat);
  const logout = useAuthStore((s) => s.logout);
  const refreshUser = useAuthStore((s) => s.refreshUser);
  const didRefresh = useRef(false);

  // Call refreshUser exactly once on mount
  useEffect(() => {
    if (!didRefresh.current) {
      didRefresh.current = true;
      refreshUser();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Start/stop token refresh only when isAuthenticated changes
  useEffect(() => {
    if (isAuthenticated) {
      startTokenRefresh(
        () => logout(),
        tokenIat ?? undefined,
      );
      return () => stopTokenRefresh();
    }
    stopTokenRefresh();
  }, [isAuthenticated, logout, tokenIat]);

  return (
    <RootErrorBoundary>
      <Outlet />
    </RootErrorBoundary>
  );
}
