import { useNavigate, useLocation } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuthStore } from "@/stores/auth";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading, user } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      const redirect = location.pathname === "/auth" || location.pathname === "/" ? undefined : location.pathname;
      navigate({ to: "/auth", search: { redirect } });
      return;
    }

    if (user?.is_locked) {
      const redirect = location.pathname === "/auth" || location.pathname === "/" ? undefined : location.pathname;
      navigate({ to: "/auth", search: { redirect } });
      return;
    }

    if (user && !user.onboarding_completed) {
      navigate({ to: "/onboarding" });
    }
  }, [isAuthenticated, isLoading, user, navigate, location.pathname]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
