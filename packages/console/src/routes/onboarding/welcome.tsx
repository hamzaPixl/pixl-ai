import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useAuthStore } from "@/stores/auth";
import { useOnboardingStore } from "@/stores/onboarding";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/onboarding/welcome")({
  component: WelcomeStep,
});

const variants = {
  enter: (dir: string) => ({ x: dir === "forward" ? 40 : -40, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: string) => ({ x: dir === "forward" ? -40 : 40, opacity: 0 }),
};

function WelcomeStep() {
  const user = useAuthStore((s) => s.user);
  const { direction, nextStep } = useOnboardingStore();
  const navigate = useNavigate();

  const handleNext = () => {
    nextStep();
    navigate({ to: "/onboarding/theme" });
  };

  return (
    <motion.div
      custom={direction}
      variants={variants}
      initial="enter"
      animate="center"
      exit="exit"
      transition={{ duration: 0.25 }}
      className="space-y-6 text-center"
    >
      <h2 className="text-2xl font-bold">
        Welcome{user?.first_name ? `, ${user.first_name}` : ""}!
      </h2>
      <p className="text-muted-foreground">
        Let's get you set up with Pixl. This will only take a minute.
      </p>
      <Button onClick={handleNext}>Get started</Button>
    </motion.div>
  );
}
