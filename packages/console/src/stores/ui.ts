/**
 * Zustand store for UI state.
 *
 * Manages sidebar, theme, and other UI preferences.
 */

import { create } from "zustand";

// Helper function to apply theme to document
function applyTheme(theme: Theme) {
  if (theme === "system") {
    // Use system preference
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (prefersDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  } else if (theme === "dark") {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

type Theme = "dark" | "light" | "system";
type ViewMode = "kanban" | "list" | "table";
type GroupBy = "none" | "status" | "epic" | "type";

interface UIStore {
  // Sidebar
  sidebarOpen: boolean;

  // Theme
  theme: Theme;

  // Auto-refresh
  autoRefreshInterval: number; // seconds, 0 = disabled

  // Features view
  featuresViewMode: ViewMode;
  featuresListGroupBy: GroupBy;
  featuresSearchQuery: string;

  // Actions
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: Theme) => void;
  setAutoRefreshInterval: (interval: number) => void;
  setFeaturesViewMode: (mode: ViewMode) => void;
  setFeaturesListGroupBy: (groupBy: GroupBy) => void;
  setFeaturesSearchQuery: (query: string) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  theme: "system",
  autoRefreshInterval: 0,
  featuresViewMode: "table",
  featuresListGroupBy: "none",
  featuresSearchQuery: "",

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setTheme: (theme) => {
    set({ theme });
    // Apply theme class to document
    applyTheme(theme);
    // Persist to localStorage
    localStorage.setItem("pixl-theme", theme);
  },
  setAutoRefreshInterval: (interval) => set({ autoRefreshInterval: interval }),
  setFeaturesViewMode: (mode) => {
    set({ featuresViewMode: mode });
    // Persist to localStorage
    localStorage.setItem("pixl-features-view", mode);
  },
  setFeaturesListGroupBy: (groupBy) => {
    set({ featuresListGroupBy: groupBy });
    localStorage.setItem("pixl-features-group-by", groupBy);
  },
  setFeaturesSearchQuery: (query) => set({ featuresSearchQuery: query }),
}));

if (typeof window !== "undefined") {
  const savedTheme = localStorage.getItem("pixl-theme") as Theme | null;
  if (savedTheme && ["dark", "light", "system"].includes(savedTheme)) {
    useUIStore.getState().setTheme(savedTheme);
  } else {
    // Default to system preference
    useUIStore.getState().setTheme("system");
  }

  // Listen for system theme changes
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  const handleSystemThemeChange = () => {
    const currentTheme = useUIStore.getState().theme;
    if (currentTheme === "system") {
      applyTheme("system");
    }
  };

  mediaQuery.addEventListener("change", handleSystemThemeChange);

  const savedViewMode = localStorage.getItem("pixl-features-view") as ViewMode | null;
  if (savedViewMode && ["kanban", "list", "table"].includes(savedViewMode)) {
    useUIStore.setState({ featuresViewMode: savedViewMode });
  }

  const savedGroupBy = localStorage.getItem("pixl-features-group-by") as GroupBy | null;
  if (savedGroupBy && ["none", "status", "epic", "type"].includes(savedGroupBy)) {
    useUIStore.setState({ featuresListGroupBy: savedGroupBy });
  }
}
