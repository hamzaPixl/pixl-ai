import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthStore } from "@/stores/auth";
import { useOnboardingStore } from "@/stores/onboarding";
import { OnboardingProgress } from "@/components/auth/OnboardingProgress";

export const Route = createFileRoute("/onboarding")({
  component: OnboardingLayout,
});

function OnboardingLayout() {
  const { isAuthenticated, isLoading } = useAuthStore();
  const { currentStep, totalSteps, error, setError } = useOnboardingStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate({ to: "/auth" });
    }
  }, [isAuthenticated, isLoading, navigate]);

  if (isLoading || !isAuthenticated) return null;

  return (
    <div className="relative min-h-svh overflow-hidden bg-background">
      {/* Left panel slides out */}
      <motion.div
        className="absolute inset-y-0 left-0 w-1/2"
        initial={{ x: 0 }}
        animate={{ x: "-100%" }}
        transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
      />
      {/* Right panel (background) slides out */}
      <motion.div
        className="absolute inset-y-0 right-0 w-1/2 hidden lg:block"
        initial={{ x: 0 }}
        animate={{ x: "100%" }}
        transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
      />

      {/* Centered onboarding content fades in */}
      <motion.div
        className="flex min-h-svh items-center justify-center px-6 py-12"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
      >
        <div className="w-full max-w-md flex flex-col gap-8">
          <OnboardingProgress
            currentStep={currentStep}
            totalSteps={totalSteps}
          />

          {error && (
            <div className="flex items-center justify-between rounded-md border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
              <span>{error}</span>
              <button
                onClick={() => setError(null)}
                className="ml-2 text-destructive hover:opacity-70"
              >
                &times;
              </button>
            </div>
          )}

          <AnimatePresence mode="wait">
            <Outlet />
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
