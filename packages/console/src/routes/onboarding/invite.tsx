import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { motion } from "framer-motion";
import { Loader2, X } from "lucide-react";
import { useOnboardingStore } from "@/stores/onboarding";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export const Route = createFileRoute("/onboarding/invite")({
  component: InviteStep,
});

const variants = {
  enter: (dir: string) => ({ x: dir === "forward" ? 40 : -40, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: string) => ({ x: dir === "forward" ? -40 : 40, opacity: 0 }),
};

function InviteStep() {
  const { workspaceId, invitedEmails, direction, setField, nextStep, prevStep } = useOnboardingStore();
  const navigate = useNavigate();
  const [emailInput, setEmailInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  const addEmail = () => {
    const trimmed = emailInput.trim();
    if (trimmed && !invitedEmails.includes(trimmed)) {
      setField("invitedEmails", [...invitedEmails, trimmed]);
      setEmailInput("");
    }
  };

  const removeEmail = (email: string) => {
    setField("invitedEmails", invitedEmails.filter((e: string) => e !== email));
  };

  const handleNext = async () => {
    if (invitedEmails.length > 0 && workspaceId) {
      setIsSending(true);
      try {
        await fetch(`/api/workspaces/${workspaceId}/invitations/bulk`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            invitations: invitedEmails.map((email: string) => ({ email, role: "editor" })),
          }),
        });
      } catch { /* ignore */ }
      setIsSending(false);
    }
    nextStep();
    navigate({ to: "/onboarding/project" });
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
        <h2 className="text-2xl font-bold">Invite your team</h2>
        <p className="mt-2 text-muted-foreground">
          Add teammates by email. You can skip this for now.
        </p>
      </div>

      <div className="flex gap-2">
        <Input
          type="email"
          value={emailInput}
          onChange={(e) => setEmailInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addEmail())}
          placeholder="teammate@example.com"
          autoFocus
        />
        <Button variant="outline" onClick={addEmail}>
          Add
        </Button>
      </div>

      {invitedEmails.length > 0 && (
        <div className="space-y-2">
          {invitedEmails.map((email: string) => (
            <div key={email} className="flex items-center justify-between rounded-md bg-muted px-3 py-2 text-sm">
              <span>{email}</span>
              <button onClick={() => removeEmail(email)} className="text-muted-foreground hover:text-foreground">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => { prevStep(); navigate({ to: "/onboarding/workspace" }); }}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Back
        </button>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => { nextStep(); navigate({ to: "/onboarding/project" }); }}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Skip
          </button>
          <Button onClick={handleNext} disabled={isSending}>
            {isSending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              "Continue"
            )}
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
