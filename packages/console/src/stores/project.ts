/**
 * Project store — manages the current project selection.
 *
 * Uses Zustand with localStorage persistence to remember
 * the last selected project across sessions.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Project } from "@/types/api";

interface ProjectState {
  /** Currently selected project ID (persisted to localStorage) */
  currentProjectId: string | null;

  /** Full project data (not persisted, loaded on selection) */
  currentProject: Project | null;

  /** List of all available projects */
  projects: Project[];

  /** Actions */
  setCurrentProject: (project: Project) => void;
  setProjects: (projects: Project[]) => void;
  clearProject: () => void;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set) => ({
      currentProjectId: null,
      currentProject: null,
      projects: [],

      setCurrentProject: (project: Project) =>
        set({
          currentProjectId: project.project_id,
          currentProject: project,
        }),

      setProjects: (projects: Project[]) => set({ projects }),

      clearProject: () =>
        set({
          currentProjectId: null,
          currentProject: null,
        }),
    }),
    {
      name: "pixl-project",
      // Only persist the project ID, not the full project data
      partialize: (state) => ({ currentProjectId: state.currentProjectId }),
    }
  )
);

// Selectors for convenient access
export const selectCurrentProjectId = (state: ProjectState) =>
  state.currentProjectId;

export const selectCurrentProject = (state: ProjectState) =>
  state.currentProject;

