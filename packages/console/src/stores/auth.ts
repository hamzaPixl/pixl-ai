import { create } from "zustand";
import { persist } from "zustand/middleware";
import { useUIStore } from "@/stores/ui";
import { setApiWorkspaceContext } from "@/lib/api";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  avatar: string | null;
  theme: string;
  onboarding_completed: number;
  is_locked: number;
  created_at: string;
  updated_at: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  workspaceId: string | null;
  tokenIat: number | null;
  sessionExpired: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  setWorkspaceId: (id: string | null) => void;
  setUser: (user: User) => void;
  refreshUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, _get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      workspaceId: null,
      tokenIat: null,
      sessionExpired: false,

      login: (_token: string, user: User) => {
        // Clear stale workspaceId — refreshUser will fetch the correct one
        set({ user, isAuthenticated: true, isLoading: false, tokenIat: null, workspaceId: null, sessionExpired: false });
        setApiWorkspaceContext(null);
        if (user.theme) {
          useUIStore.getState().setTheme(user.theme as "dark" | "light" | "system");
        }
      },

      logout: () => {
        set({ user: null, isAuthenticated: false, isLoading: false, workspaceId: null, tokenIat: null, sessionExpired: false });
        // Call backend logout to clear cookie
        fetch("/api/auth/logout", { method: "POST", credentials: "include" }).catch(() => {});
      },

      setWorkspaceId: (id: string | null) => {
        set({ workspaceId: id });
      },

      setUser: (user: User) => {
        set({ user });
      },

      refreshUser: async () => {
        try {
          const res = await fetch("/api/auth/me", { credentials: "include" });
          if (res.ok) {
            const data = await res.json();
            set({ user: data.user, isAuthenticated: true, isLoading: false, tokenIat: data.token_iat ?? null });
            if (data.user.theme) {
              useUIStore.getState().setTheme(data.user.theme as "dark" | "light" | "system");
            }
            // Single-tenant: auto-assign default workspace from /auth/me response
            const currentWsId = _get().workspaceId;
            const wsId = currentWsId ?? data.workspace_id ?? "default";
            set({ workspaceId: wsId });
            setApiWorkspaceContext(wsId);
          } else {
            // Don't force logout — just mark loading as done.
            // When auth isn't configured, 401 is expected and shouldn't
            // trigger re-renders that disrupt the session UI.
            // But skip if a login() already succeeded (race with mount refresh).
            if (_get().isAuthenticated) return;
            const hadSession = _get().workspaceId !== null;
            set((s) => ({
              ...s,
              isLoading: false,
              ...(res.status === 401 ? { workspaceId: null, sessionExpired: hadSession } : {}),
            }));
          }
        } catch {
          set((s) => ({ ...s, isLoading: false }));
        }
      },
    }),
    {
      name: "pixl-auth",
      partialize: (state) => ({ workspaceId: state.workspaceId }),
    },
  ),
);
