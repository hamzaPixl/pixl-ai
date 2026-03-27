import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";

export const Route = createFileRoute("/onboarding/")({
  component: OnboardingIndex,
});

function OnboardingIndex() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate({ to: "/onboarding/welcome", replace: true });
  }, [navigate]);

  return null;
}
