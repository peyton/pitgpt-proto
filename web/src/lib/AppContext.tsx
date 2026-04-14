import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { AppState, CompletedTrial, IngestionResult, Observation, Settings, Trial } from "./types";
import { defaultState, loadState, saveState } from "./storage";
import { appendObservationIfNew } from "./trial";

interface AppContextValue {
  state: AppState;
  setTrial: (trial: Trial | null) => void;
  addObservation: (obs: Observation) => void;
  completeTrial: (result: CompletedTrial) => void;
  updateSettings: (settings: Partial<Settings>) => void;
  restoreAll: (state: AppState) => void;
  setIngestionResult: (result: IngestionResult | null) => void;
  ingestionResult: IngestionResult | null;
  clearAll: () => void;
}

const Ctx = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(loadState);
  const [ingestionResult, setIngestionResult] = useState<IngestionResult | null>(null);

  const persist = useCallback((next: AppState | ((current: AppState) => AppState)) => {
    setState((current) => {
      const resolved = typeof next === "function" ? next(current) : next;
      saveState(resolved);
      return resolved;
    });
  }, []);

  const setTrial = useCallback(
    (trial: Trial | null) => {
      persist((current) => ({ ...current, trial }));
    },
    [persist],
  );

  const addObservation = useCallback(
    (obs: Observation) => {
      persist((current) => {
        if (!current.trial) return current;
        const updated = appendObservationIfNew(current.trial, obs);
        if (updated === current.trial) return current;
        return { ...current, trial: updated };
      });
    },
    [persist],
  );

  const completeTrial = useCallback(
    (completed: CompletedTrial) => {
      persist((current) => ({
        ...current,
        trial: null,
        completedResults: [...current.completedResults, completed],
      }));
    },
    [persist],
  );

  const updateSettings = useCallback(
    (partial: Partial<Settings>) => {
      persist((current) => ({
        ...current,
        settings: { ...current.settings, ...partial },
      }));
    },
    [persist],
  );

  const restoreAll = useCallback(
    (restored: AppState) => {
      persist(restored);
      setIngestionResult(null);
    },
    [persist],
  );

  const clearAll = useCallback(() => {
    persist(defaultState());
    setIngestionResult(null);
  }, [persist]);

  const value = useMemo(
    () => ({
      state,
      setTrial,
      addObservation,
      completeTrial,
      updateSettings,
      restoreAll,
      setIngestionResult,
      ingestionResult,
      clearAll,
    }),
    [
      state,
      setTrial,
      addObservation,
      completeTrial,
      updateSettings,
      restoreAll,
      ingestionResult,
      clearAll,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
