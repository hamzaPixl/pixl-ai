import { create } from "zustand";

interface OnboardingState {
  currentStep: number;
  totalSteps: number;
  direction: "forward" | "back";
  error: string | null;
  // Collected data
  userName: string;
  userEmail: string;
  theme: string;
  workspaceName: string;
  workspaceId: string | null;
  invitedEmails: string[];
  projectName: string;
  projectDescription: string;
  projectId: string | null;
  // Actions
  nextStep: () => void;
  prevStep: () => void;
  setField: (key: string, value: unknown) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  currentStep: 1,
  totalSteps: 6,
  direction: "forward" as "forward" | "back",
  error: null as string | null,
  userName: "",
  userEmail: "",
  theme: "system",
  workspaceName: "",
  workspaceId: null as string | null,
  invitedEmails: [] as string[],
  projectName: "",
  projectDescription: "",
  projectId: null as string | null,
};

export const useOnboardingStore = create<OnboardingState>()((set) => ({
  ...initialState,

  nextStep: () => set((s) => ({ currentStep: Math.min(s.currentStep + 1, s.totalSteps), direction: "forward" as const, error: null })),
  prevStep: () => set((s) => ({ currentStep: Math.max(s.currentStep - 1, 1), direction: "back" as const, error: null })),
  setField: (key, value) => set({ [key]: value }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
