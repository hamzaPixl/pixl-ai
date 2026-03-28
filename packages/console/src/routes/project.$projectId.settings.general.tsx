import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectSettings } from "@/lib/api";
import { FormField } from "@/components/settings/form-field";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export const Route = createFileRoute(
  "/project/$projectId/settings/general",
)({
  component: GeneralSettings,
});

function GeneralSettings() {
  const { projectId } = Route.useParams();
  const queryClient = useQueryClient();
  const queryKey = ["project-settings", "general", projectId];

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () => projectSettings.getGeneral(projectId),
  });

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (data) {
      setName(data.name);
      setDescription(data.description);
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: (d: { name?: string; description?: string }) =>
      projectSettings.updateGeneral(projectId, d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      toast.success("Settings updated");
    },
    onError: () => toast.error("Failed to update settings"),
  });

  const isDirty =
    data && (name !== data.name || description !== data.description);

  if (isLoading) {
    return (
      <div className="max-w-2xl space-y-6">
        <div>
          <h2 className="text-lg font-semibold">General</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">Loading...</p>
        </div>
        <div className="space-y-4">
          <div className="h-10 w-full animate-pulse rounded-md bg-muted" />
          <div className="h-20 w-full animate-pulse rounded-md bg-muted" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-10">
      <div>
        <h2 className="text-lg font-semibold">General</h2>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Basic project information.
        </p>
      </div>

      <section className="space-y-5">
        <FormField
          id="projectName"
          label="Project name"
          value={name}
          onChange={setName}
        />
        <FormField
          id="projectDesc"
          label="Description"
          value={description}
          onChange={setDescription}
          textarea
        />
        {data?.project_root && (
          <div className="space-y-2">
            <Label>Project root</Label>
            <p className="text-sm text-muted-foreground font-mono bg-muted px-3 py-2 rounded-md">
              {data.project_root}
            </p>
          </div>
        )}
        <div className="flex justify-end">
          <Button
            onClick={() => mutation.mutate({ name, description })}
            disabled={!isDirty || mutation.isPending}
          >
            {mutation.isPending ? "Saving..." : "Save changes"}
          </Button>
        </div>
      </section>
    </div>
  );
}
