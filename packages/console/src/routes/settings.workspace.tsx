import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/stores/auth";
import { workspacesApi, patch } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { FormField } from "@/components/settings/form-field";
import { ConfirmDialog } from "@/components/settings/confirm-dialog";
import { DangerZone } from "@/components/settings/danger-zone";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { WorkspaceMember } from "@/types/workspace";

export const Route = createFileRoute("/settings/workspace")({
  component: WorkspaceSettings,
});

function WorkspaceSettings() {
  const { workspaceId, user, setWorkspaceId } = useAuthStore();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);
  const [leaving, setLeaving] = useState(false);

  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["workspace", workspaceId],
    queryFn: () => workspacesApi.get(workspaceId!),
    enabled: !!workspaceId,
  });

  const { data: membersData } = useQuery({
    queryKey: ["workspace-members", workspaceId],
    queryFn: () => workspacesApi.members(workspaceId!),
    enabled: !!workspaceId,
  });

  const workspace = data?.workspace as Record<string, string> | undefined;
  const members = (membersData?.members ?? []) as WorkspaceMember[];
  const currentUserRole = members.find((m) => m.id === user?.id)?.role;
  const isOwner = currentUserRole === "owner";

  useEffect(() => {
    if (workspace) {
      setName(workspace.name ?? "");
      setDescription(workspace.description ?? "");
    }
  }, [workspace]);

  if (!workspaceId) {
    return (
      <div className="max-w-2xl">
        <h1 className="text-2xl font-semibold">Workspace</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          No workspace selected.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-2xl space-y-6">
        <h1 className="text-2xl font-semibold">Workspace</h1>
        <div className="space-y-4">
          <div className="h-10 w-full animate-pulse rounded-md bg-muted" />
          <div className="h-20 w-full animate-pulse rounded-md bg-muted" />
        </div>
      </div>
    );
  }

  const isDirty =
    name !== (workspace?.name ?? "") ||
    description !== (workspace?.description ?? "");

  const handleSave = async () => {
    setSaving(true);
    try {
      await patch(`/workspaces/${workspaceId}`, { name, description });
      toast.success("Workspace updated");
    } catch {
      toast.error("Failed to update workspace");
    } finally {
      setSaving(false);
    }
  };

  const handleLeave = async () => {
    setLeaving(true);
    try {
      await workspacesApi.leave(workspaceId);
      setWorkspaceId(null);
      navigate({ to: "/" });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to leave workspace";
      toast.error(message);
    } finally {
      setLeaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await workspacesApi.delete(workspaceId);
      setWorkspaceId(null);
      navigate({ to: "/" });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to delete workspace";
      toast.error(message);
    } finally {
      setDeleting(false);
    }
  };

  const canDelete = deleteConfirm === workspace?.name;

  return (
    <div className="max-w-2xl space-y-10">
      <div>
        <h1 className="text-2xl font-semibold">Workspace</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your workspace settings.
        </p>
      </div>

      <section className="space-y-5">
        <div>
          <h2 className="text-sm font-medium">General</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Update your workspace name and description.
          </p>
        </div>
        <FormField
          id="wsName"
          label="Workspace name"
          value={name}
          onChange={setName}
        />
        <FormField
          id="wsDesc"
          label="Description"
          value={description}
          onChange={setDescription}
          textarea
        />
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={!isDirty || saving}>
            {saving ? "Saving..." : "Save changes"}
          </Button>
        </div>
      </section>

      <hr className="border-border" />

      {/* Danger zone */}
      <div className="space-y-4">
        {!isOwner && currentUserRole && (
          <DangerZone
            title="Leave workspace"
            description="You will lose access to this workspace and its projects."
          >
            <Button
              variant="destructive"
              onClick={() => setLeaveDialogOpen(true)}
            >
              Leave workspace
            </Button>
            <ConfirmDialog
              open={leaveDialogOpen}
              onOpenChange={setLeaveDialogOpen}
              title="Leave workspace"
              description={
                <>
                  Are you sure you want to leave{" "}
                  <strong>{workspace?.name}</strong>? You will lose access to
                  all projects in this workspace.
                </>
              }
              confirmLabel={leaving ? "Leaving..." : "Leave workspace"}
              onConfirm={handleLeave}
              loading={leaving}
              variant="danger"
            />
          </DangerZone>
        )}

        {isOwner && (
          <DangerZone
            title="Delete workspace"
            description="Permanently delete this workspace, all members, teams, and linked projects. This action cannot be undone."
          >
            <Button
              variant="destructive"
              onClick={() => setDeleteDialogOpen(true)}
            >
              Delete workspace
            </Button>
            <ConfirmDialog
              open={deleteDialogOpen}
              onOpenChange={setDeleteDialogOpen}
              title="Delete workspace"
              description={
                <>
                  This will permanently delete{" "}
                  <strong>{workspace?.name}</strong> and all associated data.
                  This cannot be undone.
                </>
              }
              confirmLabel={deleting ? "Deleting..." : "Delete workspace"}
              onConfirm={handleDelete}
              loading={deleting}
              disabled={!canDelete}
              variant="danger"
            >
              <div className="space-y-2">
                <Label htmlFor="deleteWsConfirm">
                  Type{" "}
                  <span className="font-mono text-destructive">
                    {workspace?.name}
                  </span>{" "}
                  to confirm
                </Label>
                <Input
                  id="deleteWsConfirm"
                  value={deleteConfirm}
                  onChange={(e) => setDeleteConfirm(e.target.value)}
                />
              </div>
            </ConfirmDialog>
          </DangerZone>
        )}
      </div>
    </div>
  );
}
