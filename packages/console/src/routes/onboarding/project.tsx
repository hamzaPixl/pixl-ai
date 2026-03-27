import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { useOnboardingStore } from "@/stores/onboarding";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/onboarding/project")({
  component: ProjectStep,
});

const variants = {
  enter: (dir: string) => ({ x: dir === "forward" ? 40 : -40, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: string) => ({ x: dir === "forward" ? -40 : 40, opacity: 0 }),
};

function ProjectStep() {
  const { projectName, projectDescription, workspaceId, direction, setField, nextStep, prevStep, setError } = useOnboardingStore();
  const navigate = useNavigate();
  const [isCreating, setIsCreating] = useState(false);
  const [projectPath, setProjectPath] = useState("");

  const handleNext = async () => {
    if (projectName) {
      setIsCreating(true);
      try {
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
        const res = await fetch("/api/projects", {
          method: "POST",
          headers,
          credentials: "include",
          body: JSON.stringify({
            name: projectName,
            description: projectDescription || "",
            project_root: projectPath || null,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          setField("projectId", data.id || data.project_id);
        } else {
          const data = await res.json().catch(() => null);
          setError(data?.detail || data?.error || "Failed to create project");
          setIsCreating(false);
          return;
        }
      } catch {
        setError("Network error while creating project");
        setIsCreating(false);
        return;
      }
      setIsCreating(false);
    }
    nextStep();
    navigate({ to: "/onboarding/done" });
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
        <h2 className="text-2xl font-bold">Create your first project</h2>
        <p className="mt-2 text-muted-foreground">
          A project maps to a code repository you want to manage.
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="projectName">Project name</Label>
          <Input
            id="projectName"
            type="text"
            value={projectName}
            onChange={(e) => setField("projectName", e.target.value)}
            placeholder="my-app"
            autoFocus
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="projectDescription">Description</Label>
          <Input
            id="projectDescription"
            type="text"
            value={projectDescription}
            onChange={(e) => setField("projectDescription", e.target.value)}
            placeholder="A brief description of your project"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="projectPath">Project path</Label>
          <Input
            id="projectPath"
            type="text"
            value={projectPath}
            onChange={(e) => setProjectPath(e.target.value)}
            placeholder="/home/user/projects/my-app"
          />
          <p className="text-xs text-muted-foreground">
            Filesystem path to your project root (optional)
          </p>
        </div>
      </div>

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => { prevStep(); navigate({ to: "/onboarding/invite" }); }}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Back
        </button>
        <Button onClick={handleNext} disabled={isCreating}>
          {isCreating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating...
            </>
          ) : projectName ? (
            "Continue"
          ) : (
            "Skip"
          )}
        </Button>
      </div>
    </motion.div>
  );
}
