import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { useOnboardingStore } from "@/stores/onboarding";
import { setApiWorkspaceContext } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/onboarding/workspace")({
  component: WorkspaceStep,
});

const variants = {
  enter: (dir: string) => ({ x: dir === "forward" ? 40 : -40, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: string) => ({ x: dir === "forward" ? -40 : 40, opacity: 0 }),
};

function WorkspaceStep() {
  const user = useAuthStore((s) => s.user);
  const setWorkspaceId = useAuthStore((s) => s.setWorkspaceId);
  const { workspaceName, direction, setField, nextStep, prevStep } = useOnboardingStore();
  const navigate = useNavigate();
  const [isCreating, setIsCreating] = useState(false);

  const defaultName = user?.email
    ? user.email.split("@")[1]?.split(".")[0] || ""
    : "";

  const name = workspaceName || defaultName;

  const handleNext = async () => {
    setIsCreating(true);
    try {
      const res = await fetch("/api/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        const data = await res.json();
        const wsId = data.workspace.id;
        setField("workspaceId", wsId);
        setField("workspaceName", name);
        // Set on auth store + API context so subsequent calls include X-Workspace-ID
        setWorkspaceId(wsId);
        setApiWorkspaceContext(wsId);
      }
    } catch { /* ignore */ }
    setIsCreating(false);
    nextStep();
    navigate({ to: "/onboarding/invite" });
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
        <h2 className="text-2xl font-bold">Create your workspace</h2>
        <p className="mt-2 text-muted-foreground">
          A workspace is where your team collaborates on projects.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="wsName">Workspace name</Label>
        <Input
          id="wsName"
          type="text"
          value={name}
          onChange={(e) => setField("workspaceName", e.target.value)}
          placeholder="My Team"
          autoFocus
        />
      </div>

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => { prevStep(); navigate({ to: "/onboarding/theme" }); }}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Back
        </button>
        <Button onClick={handleNext} disabled={!name || isCreating}>
          {isCreating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating...
            </>
          ) : (
            "Continue"
          )}
        </Button>
      </div>
    </motion.div>
  );
}
