import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectSettings } from "@/lib/api";
import type { EnvVar } from "@/lib/api/projects";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { Plus, Trash2, Eye, EyeOff } from "lucide-react";

export const Route = createFileRoute(
  "/project/$projectId/settings/environment",
)({
  component: EnvironmentSettings,
});

function EnvironmentSettings() {
  const { projectId } = Route.useParams();
  const queryClient = useQueryClient();
  const queryKey = ["project-settings", "env-vars", projectId];

  const { data: envVars = [], isLoading } = useQuery({
    queryKey,
    queryFn: () => projectSettings.listEnvVars(projectId),
  });

  const [showForm, setShowForm] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newIsSecret, setNewIsSecret] = useState(false);
  const [revealedKeys, setRevealedKeys] = useState<Set<string>>(new Set());

  const upsertMutation = useMutation({
    mutationFn: (d: { key: string; value: string; is_secret?: boolean }) =>
      projectSettings.upsertEnvVar(projectId, d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      setShowForm(false);
      setNewKey("");
      setNewValue("");
      setNewIsSecret(false);
      toast.success("Variable saved");
    },
    onError: () => toast.error("Failed to save variable"),
  });

  const deleteMutation = useMutation({
    mutationFn: (key: string) => projectSettings.deleteEnvVar(projectId, key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      toast.success("Variable deleted");
    },
    onError: () => toast.error("Failed to delete variable"),
  });

  const toggleReveal = (key: string) => {
    setRevealedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="max-w-2xl space-y-6">
        <div>
          <h2 className="text-lg font-semibold">Environment</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">Loading...</p>
        </div>
        <div className="h-32 w-full animate-pulse rounded-md bg-muted" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-10">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold">Environment</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Variables injected into sandbox containers at runtime.
          </p>
        </div>
        {!showForm && (
          <Button size="sm" variant="outline" onClick={() => setShowForm(true)}>
            <Plus className="mr-1 h-3.5 w-3.5" />
            Add variable
          </Button>
        )}
      </div>

      {showForm && (
        <div className="rounded-lg border p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Key</Label>
              <Input
                placeholder="MY_API_KEY"
                value={newKey}
                onChange={(e) =>
                  setNewKey(
                    e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, ""),
                  )
                }
              />
            </div>
            <div className="space-y-1">
              <Label>Value</Label>
              <Input
                placeholder="value"
                type={newIsSecret ? "password" : "text"}
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={newIsSecret}
              onCheckedChange={setNewIsSecret}
              id="is-secret"
            />
            <Label htmlFor="is-secret" className="text-sm">
              Secret (masked in UI)
            </Label>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() =>
                upsertMutation.mutate({
                  key: newKey,
                  value: newValue,
                  is_secret: newIsSecret,
                })
              }
              disabled={!newKey || !newValue || upsertMutation.isPending}
            >
              Save
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {envVars.length === 0 && !showForm ? (
        <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          No environment variables configured yet.
        </div>
      ) : (
        envVars.length > 0 && (
          <div className="rounded-lg border divide-y">
            {envVars.map((v: EnvVar) => (
              <div
                key={v.key}
                className="flex items-center justify-between px-4 py-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <code className="text-sm font-medium">{v.key}</code>
                  <span className="text-sm text-muted-foreground font-mono truncate max-w-xs">
                    {v.is_secret && !revealedKeys.has(v.key)
                      ? "••••••••"
                      : v.value}
                  </span>
                  {v.is_secret && (
                    <button
                      onClick={() => toggleReveal(v.key)}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      {revealedKeys.has(v.key) ? (
                        <EyeOff className="h-3.5 w-3.5" />
                      ) : (
                        <Eye className="h-3.5 w-3.5" />
                      )}
                    </button>
                  )}
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => deleteMutation.mutate(v.key)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
