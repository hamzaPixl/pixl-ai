import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { motion } from "framer-motion";
import { useAuthStore, type User } from "@/stores/auth";
import { SplitLayout } from "@/components/auth/SplitLayout";
import { AuthBackground } from "@/components/auth/AuthBackground";
import { AuthForm } from "@/components/auth/AuthForm";

export const Route = createFileRoute("/auth")({
  component: AuthPage,
  validateSearch: (
    search: Record<string, unknown>
  ): { mode?: string; redirect?: string } => ({
    mode: typeof search.mode === "string" ? search.mode : undefined,
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
});

function AuthPage() {
  const login = useAuthStore((s) => s.login);
  const refreshUser = useAuthStore((s) => s.refreshUser);
  const navigate = useNavigate();
  const sessionExpired = useAuthStore((s) => s.sessionExpired);
  const { mode, redirect: redirectTo } = Route.useSearch();
  const [error, setError] = useState(sessionExpired ? "Your session has expired. Please sign in again." : "");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (email: string, password: string) => {
    setError("");
    setIsLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.error?.message || data.error || "Login failed");
        return;
      }
      const data = await res.json();
      login(data.token, data.user as User);
      // Fetch workspace before navigating so X-Workspace-ID is ready
      await refreshUser();
      const dest = redirectTo && redirectTo !== "/auth" ? redirectTo : "/";
      navigate({ to: dest });
    } catch {
      setError("Network error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignup = async (data: {
    firstName: string;
    lastName: string;
    email: string;
    password: string;
  }) => {
    setError("");
    setIsLoading(true);
    try {
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          email: data.email,
          password: data.password,
          first_name: data.firstName,
          last_name: data.lastName,
        }),
      });
      if (!res.ok) {
        const d = await res.json();
        setError(d.error?.message || d.error || "Signup failed");
        return;
      }
      const d = await res.json();
      login(d.token, d.user as User);
      navigate({ to: "/onboarding" });
    } catch {
      setError("Network error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SplitLayout
      left={
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <AuthForm
            initialMode={mode === "signup" ? "signup" : "login"}
            onLogin={handleLogin}
            onSignup={handleSignup}
            error={error}
            isLoading={isLoading}
          />
        </motion.div>
      }
      right={<AuthBackground />}
    />
  );
}
