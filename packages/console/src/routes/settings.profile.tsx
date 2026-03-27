import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useAuthStore } from "@/stores/auth";
import { auth } from "@/lib/api";
import { toast } from "sonner";
import { useUIStore } from "@/stores/ui";
import { Sun, Moon, Monitor } from "lucide-react";
import { FormField } from "@/components/settings/form-field";
import { ConfirmDialog } from "@/components/settings/confirm-dialog";
import { DangerZone } from "@/components/settings/danger-zone";
import { UserAvatar } from "@/components/user-avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { User } from "@/stores/auth";

const themes = [
  {
    value: "light" as const,
    label: "Light",
    icon: Sun,
    desc: "Light background with dark text",
  },
  {
    value: "dark" as const,
    label: "Dark",
    icon: Moon,
    desc: "Dark background with light text",
  },
  {
    value: "system" as const,
    label: "System",
    icon: Monitor,
    desc: "Follows your OS preference",
  },
];

export const Route = createFileRoute("/settings/profile")({
  component: ProfileSettings,
});

function ProfileSettings() {
  const { user, setUser, logout } = useAuthStore();
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [saving, setSaving] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  if (!user) return null;

  const isDirty = firstName !== user.first_name || lastName !== user.last_name;

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await auth.updateProfile({
        first_name: firstName,
        last_name: lastName,
      });
      setUser(res.user as User);
      toast.success("Profile updated");
    } catch {
      toast.error("Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      toast.error("New password must be at least 8 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    setChangingPassword(true);
    try {
      await auth.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success("Password changed");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch {
      toast.error("Failed to change password");
    } finally {
      setChangingPassword(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleting(true);
    try {
      await auth.deleteAccount({ password: deletePassword });
      logout();
      navigate({ to: "/" });
    } catch (err: unknown) {
      const fallback = "Failed to delete account";
      let message = fallback;
      if (err && typeof err === "object" && "body" in err) {
        const body = (err as { body: Record<string, unknown> }).body;
        const errObj = body?.error;
        if (
          errObj &&
          typeof errObj === "object" &&
          "message" in (errObj as Record<string, unknown>)
        ) {
          message = (errObj as { message: string }).message;
        }
      } else if (err instanceof Error) {
        message = err.message;
      }
      toast.error(message || fallback);
    } finally {
      setDeleting(false);
    }
  };

  const canChangePassword = currentPassword && newPassword && confirmPassword;
  const canDelete = deletePassword && deleteConfirm === "DELETE";

  return (
    <div className="max-w-2xl space-y-10">
      <div>
        <h1 className="text-2xl font-semibold">Profile</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your personal information.
        </p>
      </div>

      {/* Profile info */}
      <section className="space-y-5">
        <div className="flex items-center gap-4">
          <UserAvatar
            firstName={user.first_name}
            lastName={user.last_name}
            size="lg"
          />
          <div>
            <p className="font-medium">
              {user.first_name} {user.last_name}
            </p>
            <p className="text-sm text-muted-foreground">{user.email}</p>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            id="firstName"
            label="First name"
            value={firstName}
            onChange={setFirstName}
          />
          <FormField
            id="lastName"
            label="Last name"
            value={lastName}
            onChange={setLastName}
          />
        </div>
        <FormField
          id="email"
          label="Email"
          value={user.email}
          onChange={() => {}}
          disabled
          hint="Email cannot be changed."
        />
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={!isDirty || saving}>
            {saving ? "Saving..." : "Save changes"}
          </Button>
        </div>
      </section>

      <hr className="border-border" />

      {/* Password */}
      <section className="space-y-5">
        <div>
          <h2 className="text-sm font-medium">Change password</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Update your password to keep your account secure.
          </p>
        </div>
        <form onSubmit={handleChangePassword} className="space-y-4">
          <FormField
            id="currentPassword"
            label="Current password"
            type="password"
            value={currentPassword}
            onChange={setCurrentPassword}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="newPassword"
              label="New password"
              type="password"
              value={newPassword}
              onChange={setNewPassword}
              placeholder="Min 8 characters"
            />
            <FormField
              id="confirmPassword"
              label="Confirm new password"
              type="password"
              value={confirmPassword}
              onChange={setConfirmPassword}
            />
          </div>
          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={!canChangePassword || changingPassword}
            >
              {changingPassword ? "Changing..." : "Change password"}
            </Button>
          </div>
        </form>
      </section>

      <hr className="border-border" />

      {/* Theme */}
      <ThemePicker />

      <hr className="border-border" />

      {/* Danger zone */}
      <DangerZone
        title="Delete account"
        description="Permanently delete your account and all associated data. This action cannot be undone."
      >
        <Button variant="destructive" onClick={() => setDeleteDialogOpen(true)}>
          Delete account
        </Button>
        <ConfirmDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          title="Delete account"
          description="This will permanently delete your account and remove you from all workspaces. This cannot be undone. If you are the sole owner of a workspace, you must transfer ownership first."
          confirmLabel={deleting ? "Deleting..." : "Delete my account"}
          onConfirm={handleDeleteAccount}
          loading={deleting}
          disabled={!canDelete}
          variant="danger"
        >
          <FormField
            id="deletePassword"
            label="Password"
            type="password"
            value={deletePassword}
            onChange={setDeletePassword}
            placeholder="Enter your password"
          />
          <div className="space-y-2">
            <Label htmlFor="deleteConfirm">
              Type <span className="font-mono text-destructive">DELETE</span> to
              confirm
            </Label>
            <Input
              id="deleteConfirm"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
            />
          </div>
        </ConfirmDialog>
      </DangerZone>
    </div>
  );
}

function ThemePicker() {
  const { theme, setTheme } = useUIStore();

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-sm font-medium">Theme</h2>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Select your preferred theme for the application.
        </p>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {themes.map((t) => (
          <button
            key={t.value}
            onClick={() => {
              setTheme(t.value);
              auth.updateProfile({ theme: t.value }).catch(() => {
                toast.error("Failed to save theme preference");
              });
            }}
            className={cn(
              "flex flex-col items-center gap-3 rounded-lg border-2 p-4 transition-all",
              theme === t.value
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/40",
            )}
          >
            <t.icon
              className={cn(
                "h-6 w-6",
                theme === t.value ? "text-primary" : "text-muted-foreground",
              )}
            />
            <div className="text-center">
              <p className="text-sm font-medium">{t.label}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{t.desc}</p>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
