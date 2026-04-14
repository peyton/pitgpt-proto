import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { AppState, CompletedTrial, IngestionResult, Observation, Settings, Trial } from "./types";
import { loadState, saveState } from "./storage";

interface AppContextValue {
  state: AppState;
  setTrial: (trial: Trial | null) => void;
  addObservation: (obs: Observation) => void;
  completeTrial: (result: CompletedTrial) => void;
  updateSettings: (settings: Partial<Settings>) => void;
  setIngestionResult: (result: IngestionResult | null) => void;
  ingestionResult: IngestionResult | null;
  clearAll: () => void;
}

const Ctx = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(loadState);
  const [ingestionResult, setIngestionResult] = useState<IngestionResult | null>(null);

  const persist = useCallback((next: AppState) => {
    setState(next);
    saveState(next);
  }, []);

  const setTrial = useCallback(
    (trial: Trial | null) => {
      persist({ ...state, trial });
    },
    [state, persist],
  );

  const addObservation = useCallback(
    (obs: Observation) => {
      if (!state.trial) return;
      const updated = {
        ...state.trial,
        observations: [...state.trial.observations, obs],
      };
      persist({ ...state, trial: updated });
    },
    [state, persist],
  );

  const completeTrial = useCallback(
    (completed: CompletedTrial) => {
      persist({
        ...state,
        trial: null,
        completedResults: [...state.completedResults, completed],
      });
    },
    [state, persist],
  );

  const updateSettings = useCallback(
    (partial: Partial<Settings>) => {
      persist({
        ...state,
        settings: { ...state.settings, ...partial },
      });
    },
    [state, persist],
  );

  const clearAll = useCallback(() => {
    const fresh: AppState = {
      trial: null,
      completedResults: [],
      settings: {
        reminderEnabled: true,
        reminderTime: "21:00",
        emailReminderEnabled: false,
      },
    };
    persist(fresh);
    setIngestionResult(null);
  }, [persist]);

  const value = useMemo(
    () => ({
      state,
      setTrial,
      addObservation,
      completeTrial,
      updateSettings,
      setIngestionResult,
      ingestionResult,
      clearAll,
    }),
    [state, setTrial, addObservation, completeTrial, updateSettings, ingestionResult, clearAll],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
