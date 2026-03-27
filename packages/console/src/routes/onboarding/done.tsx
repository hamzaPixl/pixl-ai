import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { useOnboardingStore } from "@/stores/onboarding";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/onboarding/done")({
  component: DoneStep,
});

const variants = {
  enter: (dir: string) => ({ x: dir === "forward" ? 40 : -40, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: string) => ({ x: dir === "forward" ? -40 : 40, opacity: 0 }),
};

function DoneStep() {
  const { refreshUser } = useAuthStore();
  const { direction, reset } = useOnboardingStore();
  const navigate = useNavigate();
  const [completing, setCompleting] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const complete = async () => {
      try {
        const res = await fetch("/api/auth/me/onboarding-complete", {
          method: "POST",
          credentials: "include",
        });
        if (!res.ok) {
          setFailed(true);
          setCompleting(false);
          return;
        }
        await refreshUser();
      } catch {
        setFailed(true);
      }
      setCompleting(false);
    };
    complete();
  }, [refreshUser]);

  const handleFinish = async () => {
    if (failed) {
      // Retry the onboarding-complete call
      try {
        const res = await fetch("/api/auth/me/onboarding-complete", {
          method: "POST",
          credentials: "include",
        });
        if (res.ok) await refreshUser();
      } catch { /* navigate anyway */ }
    }
    reset();
    navigate({ to: "/" });
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
        {completing ? "Setting things up..." : failed ? "Almost there" : "You're all set!"}
      </h2>
      <p className="text-muted-foreground">
        {completing
          ? "Just a moment..."
          : failed
            ? "Something went wrong, but you can continue."
            : "Your workspace is ready. Let's build something great."}
      </p>
      {completing ? (
        <Loader2 className="mx-auto h-6 w-6 animate-spin text-primary" />
      ) : (
        <Button onClick={handleFinish}>
          {failed ? "Try again & continue" : "Go to dashboard"}
        </Button>
      )}
    </motion.div>
  );
}
