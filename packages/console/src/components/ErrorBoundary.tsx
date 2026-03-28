/**
 * Reusable error boundary with retry button.
 */

import { Component, type ReactNode, type ErrorInfo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex flex-col items-center gap-3 py-8">
            <AlertTriangle className="h-8 w-8 text-destructive" />
            <p className="text-sm font-medium text-destructive">
              Something went wrong
            </p>
            <p className="text-xs text-muted-foreground font-mono max-w-md text-center">
              {this.state.error.message}
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => this.setState({ error: null })}
              className="gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </Button>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}
