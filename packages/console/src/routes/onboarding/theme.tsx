import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useOnboardingStore } from "@/stores/onboarding";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/onboarding/theme")({
  component: ThemeStep,
});

const variants = {
  enter: (dir: string) => ({ x: dir === "forward" ? 40 : -40, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: string) => ({ x: dir === "forward" ? -40 : 40, opacity: 0 }),
};

function ThemeStep() {
  const { theme, direction, setField, nextStep, prevStep } = useOnboardingStore();
  const navigate = useNavigate();

  const themes = [
    { value: "light", label: "Light" },
    { value: "dark", label: "Dark" },
    { value: "system", label: "System" },
  ];

  const handleNext = () => {
    nextStep();
    navigate({ to: "/onboarding/workspace" });
  };

  return (
    <motion.div
      custom={direction}
      variants={variants}
      initial="enter"
      animate="center"
      exit="exit"
      transition={{ duration: 0.25 }}
      className="space-y-6"
    >
      <div className="text-center">
        <h2 className="text-2xl font-bold">Choose your theme</h2>
        <p className="mt-2 text-muted-foreground">You can change this later in settings.</p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {themes.map((t) => (
          <button
            key={t.value}
            onClick={() => setField("theme", t.value)}
            className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-colors ${
              theme === t.value
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50"
            }`}
          >
            <span className="text-sm font-medium">{t.label}</span>
          </button>
        ))}
      </div>

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => { prevStep(); navigate({ to: "/onboarding/welcome" }); }}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Back
        </button>
        <Button onClick={handleNext}>Continue</Button>
      </div>
    </motion.div>
  );
}
