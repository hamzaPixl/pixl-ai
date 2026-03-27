import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useAuthStore } from "@/stores/auth";
import { workspacesApi, del } from "@/lib/api";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { UserPlus, Trash2, X, Plus, ArrowLeft } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { FormField } from "@/components/settings/form-field";
import { ConfirmDialog } from "@/components/settings/confirm-dialog";
import { UserAvatar } from "@/components/user-avatar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  WorkspaceMember,
  Invitation,
  Team,
  TeamMember,
} from "@/types/workspace";

export const Route = createFileRoute("/settings/members")({
  component: MembersSettings,
});

function MembersSettings() {
  const { workspaceId, user } = useAuthStore();
  const queryClient = useQueryClient();
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("editor");
  const [inviting, setInviting] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["workspace-members", workspaceId],
    queryFn: () => workspacesApi.members(workspaceId!),
    enabled: !!workspaceId,
  });

  const { data: invitationsData } = useQuery({
    queryKey: ["workspace-invitations", workspaceId],
    queryFn: () => workspacesApi.invitations(workspaceId!),
    enabled: !!workspaceId,
  });

  const members = (data?.members ?? []) as WorkspaceMember[];
  const invitations = (invitationsData?.invitations ?? []) as Invitation[];
  const currentUserRole = members.find((m) => m.id === user?.id)?.role;
  const isOwner = currentUserRole === "owner";

  if (!workspaceId) {
    return (
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold">Members</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          No workspace selected.
        </p>
      </div>
    );
  }

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setInviting(true);
    try {
      await workspacesApi.invite(workspaceId, {
        email: inviteEmail.trim(),
        role: inviteRole,
      });
      toast.success("Invitation sent");
      setInviteEmail("");
      queryClient.invalidateQueries({
        queryKey: ["workspace-members", workspaceId],
      });
      queryClient.invalidateQueries({
        queryKey: ["workspace-invitations", workspaceId],
      });
    } catch {
      toast.error("Failed to send invitation");
    } finally {
      setInviting(false);
    }
  };

  const handleRemove = async (memberId: string) => {
    try {
      await del(`/workspaces/${workspaceId}/members/${memberId}`);
      toast.success("Member removed");
      queryClient.invalidateQueries({
        queryKey: ["workspace-members", workspaceId],
      });
    } catch {
      toast.error("Failed to remove member");
    }
  };

  const handleRoleChange = async (memberId: string, newRole: string) => {
    try {
      await workspacesApi.changeRole(workspaceId, memberId, newRole);
      toast.success("Role updated");
      queryClient.invalidateQueries({
        queryKey: ["workspace-members", workspaceId],
      });
    } catch {
      toast.error("Failed to change role");
    }
  };

  const handleRevokeInvitation = async (invId: string) => {
    try {
      await workspacesApi.revokeInvitation(workspaceId, invId);
      toast.success("Invitation revoked");
      queryClient.invalidateQueries({
        queryKey: ["workspace-invitations", workspaceId],
      });
    } catch {
      toast.error("Failed to revoke invitation");
    }
  };

  const roleBadgeColor = (role: string) => {
    switch (role) {
      case "owner":
        return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 border-transparent";
      case "editor":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 border-transparent";
      case "viewer":
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400 border-transparent";
      default:
        return "bg-gray-100 text-gray-800 border-transparent";
    }
  };

  const roles = ["owner", "editor", "viewer"];

  return (
    <div className="max-w-3xl space-y-10">
      <div>
        <h1 className="text-2xl font-semibold">Members</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage who has access to this workspace.
        </p>
      </div>

      {/* Invite form */}
      <form onSubmit={handleInvite} className="flex gap-2">
        <Input
          type="email"
          value={inviteEmail}
          onChange={(e) => setInviteEmail(e.target.value)}
          placeholder="colleague@company.com"
          className="flex-1"
        />
        <Select value={inviteRole} onValueChange={setInviteRole}>
          <SelectTrigger className="w-[130px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="viewer">Viewer</SelectItem>
            <SelectItem value="editor">Editor</SelectItem>
            <SelectItem value="owner">Owner</SelectItem>
          </SelectContent>
        </Select>
        <Button
          type="submit"
          size="sm"
          disabled={inviting || !inviteEmail.trim()}
        >
          <UserPlus className="h-4 w-4" />
          Invite
        </Button>
      </form>

      {/* Member list */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground">
          {members.length} member{members.length !== 1 ? "s" : ""}
        </h2>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="h-9 w-9 animate-pulse rounded-full bg-muted" />
                <div className="flex-1 space-y-1">
                  <div className="h-4 w-32 animate-pulse rounded bg-muted" />
                  <div className="h-3 w-48 animate-pulse rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="divide-y divide-border">
            {members.map((member) => {
              const isCurrentUser = member.id === user?.id;
              return (
                <div key={member.id} className="flex items-center gap-3 py-3">
                  <UserAvatar
                    firstName={member.first_name}
                    lastName={member.last_name}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {member.first_name} {member.last_name}
                      {isCurrentUser && (
                        <span className="ml-1 text-muted-foreground">
                          (you)
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {member.email}
                    </p>
                  </div>
                  {isOwner && !isCurrentUser ? (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="outline"
                          size="sm"
                          className={`h-auto rounded-full px-2 py-0.5 text-xs capitalize ${roleBadgeColor(member.role)}`}
                        >
                          {member.role}
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {roles.map((role) => (
                          <DropdownMenuItem
                            key={role}
                            onClick={() => handleRoleChange(member.id, role)}
                            className={
                              member.role === role ? "font-semibold" : ""
                            }
                          >
                            <span className="capitalize">{role}</span>
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  ) : (
                    <Badge
                      className={`shrink-0 rounded-full capitalize ${roleBadgeColor(member.role)}`}
                    >
                      {member.role}
                    </Badge>
                  )}
                  {!isCurrentUser && isOwner && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={() => handleRemove(member.id)}
                      title="Remove member"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Pending invitations */}
      {invitations.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">
            Pending invitations
          </h2>
          <div className="divide-y divide-border">
            {invitations.map((inv) => (
              <div key={inv.id} className="flex items-center gap-3 py-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground">
                  {inv.email[0]?.toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{inv.email}</p>
                  <p className="text-xs text-muted-foreground">
                    Invited {new Date(inv.created_at).toLocaleDateString()}
                  </p>
                </div>
                <Badge
                  className={`shrink-0 rounded-full capitalize ${roleBadgeColor(inv.role)}`}
                >
                  {inv.role}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => handleRevokeInvitation(inv.id)}
                  title="Revoke invitation"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </section>
      )}

      <hr className="border-border" />

      {/* Teams */}
      <TeamsSection workspaceId={workspaceId} />
    </div>
  );
}

// ─── Teams Section ──────────────────────────────────────────

const TEAM_COLORS = [
  "#ef4444",
  "#f97316",
  "#eab308",
  "#22c55e",
  "#06b6d4",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
];

function TeamsSection({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient();

  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newColor, setNewColor] = useState(TEAM_COLORS[5]);
  const [creating, setCreating] = useState(false);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const { data: teamsData, isLoading } = useQuery({
    queryKey: ["workspace-teams", workspaceId],
    queryFn: () => workspacesApi.teams(workspaceId),
    enabled: !!workspaceId,
  });

  const { data: membersData } = useQuery({
    queryKey: ["workspace-members", workspaceId],
    queryFn: () => workspacesApi.members(workspaceId),
    enabled: !!workspaceId,
  });

  const selectedTeam = selectedTeamId
    ? (teamsData?.teams as Team[] | undefined)?.find(
        (t) => t.id === selectedTeamId,
      )
    : null;

  const { data: teamMembersData } = useQuery({
    queryKey: ["team-members", workspaceId, selectedTeamId],
    queryFn: () => workspacesApi.teamMembers(workspaceId, selectedTeamId!),
    enabled: !!workspaceId && !!selectedTeamId,
  });

  const teams = (teamsData?.teams ?? []) as Team[];
  const workspaceMembers = (membersData?.members ?? []) as WorkspaceMember[];
  const teamMembers = (teamMembersData?.members ?? []) as TeamMember[];
  const teamMemberIds = new Set(teamMembers.map((m) => m.id));

  const invalidateTeams = () => {
    queryClient.invalidateQueries({
      queryKey: ["workspace-teams", workspaceId],
    });
  };

  const invalidateTeamMembers = () => {
    queryClient.invalidateQueries({
      queryKey: ["team-members", workspaceId, selectedTeamId],
    });
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await workspacesApi.createTeam(workspaceId, {
        name: newName.trim(),
        description: newDescription.trim() || undefined,
        color: newColor,
      });
      toast.success("Team created");
      setNewName("");
      setNewDescription("");
      setNewColor(TEAM_COLORS[5]);
      setShowCreate(false);
      invalidateTeams();
    } catch {
      toast.error("Failed to create team");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedTeamId) return;
    setDeleting(true);
    try {
      await workspacesApi.deleteTeam(workspaceId, selectedTeamId);
      toast.success("Team deleted");
      setSelectedTeamId(null);
      setDeleteDialogOpen(false);
      invalidateTeams();
    } catch {
      toast.error("Failed to delete team");
    } finally {
      setDeleting(false);
    }
  };

  const handleAddMember = async (userId: string) => {
    if (!selectedTeamId) return;
    try {
      await workspacesApi.addTeamMember(workspaceId, selectedTeamId, userId);
      toast.success("Member added");
      invalidateTeamMembers();
    } catch {
      toast.error("Failed to add member");
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selectedTeamId) return;
    try {
      await workspacesApi.removeTeamMember(workspaceId, selectedTeamId, userId);
      toast.success("Member removed");
      invalidateTeamMembers();
    } catch {
      toast.error("Failed to remove member");
    }
  };

  // Team detail view
  if (selectedTeam) {
    const availableMembers = workspaceMembers.filter(
      (m) => !teamMemberIds.has(m.id),
    );

    return (
      <div className="space-y-6">
        <div>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 text-muted-foreground mb-4"
            onClick={() => setSelectedTeamId(null)}
          >
            <ArrowLeft className="h-4 w-4" />
            Back to teams
          </Button>
          <div className="flex items-center gap-3">
            <div
              className="h-4 w-4 rounded-full shrink-0"
              style={{ backgroundColor: selectedTeam.color ?? "#3b82f6" }}
            />
            <h2 className="text-lg font-semibold">{selectedTeam.name}</h2>
          </div>
          {selectedTeam.description && (
            <p className="mt-1 text-sm text-muted-foreground">
              {selectedTeam.description}
            </p>
          )}
        </div>

        <section className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
            {teamMembers.length} member{teamMembers.length !== 1 ? "s" : ""}
          </h3>
          {teamMembers.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              No members yet.
            </p>
          ) : (
            <div className="divide-y divide-border">
              {teamMembers.map((member) => (
                <div key={member.id} className="flex items-center gap-3 py-3">
                  <UserAvatar
                    firstName={member.first_name}
                    lastName={member.last_name}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {member.first_name} {member.last_name}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {member.email}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => handleRemoveMember(member.id)}
                    title="Remove from team"
                  >
                    <X />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </section>

        {availableMembers.length > 0 && (
          <section className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground">
              Add members
            </h3>
            <div className="divide-y divide-border">
              {availableMembers.map((member) => (
                <div key={member.id} className="flex items-center gap-3 py-3">
                  <UserAvatar
                    firstName={member.first_name}
                    lastName={member.last_name}
                    muted
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {member.first_name} {member.last_name}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {member.email}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1"
                    onClick={() => handleAddMember(member.id)}
                  >
                    <UserPlus className="h-3.5 w-3.5" />
                    Add
                  </Button>
                </div>
              ))}
            </div>
          </section>
        )}

        <Button
          variant="link"
          className="gap-1.5 text-destructive p-0 h-auto"
          onClick={() => setDeleteDialogOpen(true)}
        >
          <Trash2 className="h-4 w-4" />
          Delete team
        </Button>
        <ConfirmDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          title="Delete team"
          description={
            <>
              Are you sure you want to delete{" "}
              <strong>{selectedTeam.name}</strong>? This will remove all members
              from the team.
            </>
          }
          confirmLabel={deleting ? "Deleting..." : "Delete team"}
          onConfirm={handleDelete}
          loading={deleting}
          variant="danger"
        />
      </div>
    );
  }

  // Team list view
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium">Teams</h2>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5"
          onClick={() => setShowCreate(!showCreate)}
        >
          <Plus className="h-4 w-4" />
          New team
        </Button>
      </div>

      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="space-y-4 rounded-lg border border-border p-4"
        >
          <FormField
            id="teamName"
            label="Team name"
            value={newName}
            onChange={setNewName}
            placeholder="e.g. Engineering"
          />
          <FormField
            id="teamDesc"
            label="Description"
            value={newDescription}
            onChange={setNewDescription}
            placeholder="What does this team do?"
            textarea
          />
          <div className="space-y-2">
            <Label>Color</Label>
            <div className="flex gap-2">
              {TEAM_COLORS.map((color) => (
                <button
                  key={color}
                  type="button"
                  onClick={() => setNewColor(color)}
                  className={`h-7 w-7 rounded-full transition-all ${
                    newColor === color
                      ? "ring-2 ring-ring ring-offset-2 ring-offset-background"
                      : ""
                  }`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowCreate(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!newName.trim() || creating}>
              {creating ? "Creating..." : "Create team"}
            </Button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : teams.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No teams yet. Create one to get started.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-border">
          {teams.map((team) => (
            <button
              key={team.id}
              onClick={() => setSelectedTeamId(team.id)}
              className="flex w-full items-center gap-3 py-3 text-left transition-colors hover:bg-accent/50 rounded-md px-2 -mx-2"
            >
              <div
                className="h-3 w-3 rounded-full shrink-0"
                style={{ backgroundColor: team.color ?? "#3b82f6" }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{team.name}</p>
                {team.description && (
                  <p className="text-xs text-muted-foreground truncate">
                    {team.description}
                  </p>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
