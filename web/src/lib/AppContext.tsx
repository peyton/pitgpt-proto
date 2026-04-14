import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  createExperimentConversation,
  createExperimentMessage,
  statusFromIngestionResult,
  type ExperimentMessageInput,
} from "./experiments";
import type {
  AppState,
  CompletedTrial,
  ExperimentConversation,
  ExperimentStatus,
  IngestionResult,
  Observation,
  Settings,
  Trial,
} from "./types";
import { defaultState, loadState, loadStateAsync, saveState } from "./storage";
import { appendObservationIfNew } from "./trial";

interface AppContextValue {
  state: AppState;
  setTrial: (trial: Trial | null) => void;
  addObservation: (obs: Observation) => void;
  completeTrial: (result: CompletedTrial) => void;
  updateSettings: (settings: Partial<Settings>) => void;
  restoreAll: (state: AppState) => void;
  createExperiment: (input: {
    query: string;
    documents?: string[];
    sourceNames?: string[];
    ingestionResult?: IngestionResult | null;
    status?: ExperimentStatus;
  }) => ExperimentConversation;
  appendExperimentMessage: (experimentId: string, message: ExperimentMessageInput) => void;
  setExperimentStatus: (experimentId: string, status: ExperimentStatus) => void;
  setExperimentResult: (experimentId: string, result: IngestionResult) => void;
  reviseExperimentRequest: (experimentId: string, query: string) => void;
  markExperimentRead: (experimentId: string) => void;
  setCurrentExperiment: (experimentId: string | null) => void;
  linkExperimentTrial: (experimentId: string, trialId: string) => void;
  setIngestionResult: (result: IngestionResult | null, experimentId?: string | null) => void;
  ingestionResult: IngestionResult | null;
  protocolExperimentId: string | null;
  clearAll: () => void;
}

const Ctx = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(loadState);
  const [ingestionResult, setIngestionResult] = useState<IngestionResult | null>(null);
  const [protocolExperimentId, setProtocolExperimentId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void loadStateAsync().then((loaded) => {
      if (active) setState(loaded);
    });
    return () => {
      active = false;
    };
  }, []);

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
      const completedAt = new Date().toISOString();
      persist((current) => ({
        ...current,
        trial: null,
        experiments: current.experiments.map((experiment) =>
          experiment.trialId === completed.trial.id
            ? { ...experiment, status: "completed", updatedAt: completedAt }
            : experiment,
        ),
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
      setProtocolExperimentId(null);
    },
    [persist],
  );

  const clearAll = useCallback(() => {
    persist(defaultState());
    setIngestionResult(null);
    setProtocolExperimentId(null);
  }, [persist]);

  const createExperiment = useCallback(
    (input: {
      query: string;
      documents?: string[];
      sourceNames?: string[];
      ingestionResult?: IngestionResult | null;
      status?: ExperimentStatus;
    }) => {
      const experiment = createExperimentConversation(input);
      persist((current) => ({
        ...current,
        experiments: [experiment, ...current.experiments],
        currentExperimentId: experiment.id,
      }));
      return experiment;
    },
    [persist],
  );

  const appendExperimentMessage = useCallback(
    (experimentId: string, messageInput: ExperimentMessageInput) => {
      const message = createExperimentMessage(messageInput);
      persist((current) => ({
        ...current,
        experiments: current.experiments.map((experiment) => {
          if (experiment.id !== experimentId) return experiment;
          return {
            ...experiment,
            messages: [...experiment.messages, message],
            updatedAt: message.createdAt,
            unread: current.currentExperimentId !== experimentId && message.role !== "user",
          };
        }),
      }));
    },
    [persist],
  );

  const setExperimentStatus = useCallback(
    (experimentId: string, status: ExperimentStatus) => {
      const updatedAt = new Date().toISOString();
      persist((current) => ({
        ...current,
        experiments: current.experiments.map((experiment) =>
          experiment.id === experimentId ? { ...experiment, status, updatedAt } : experiment,
        ),
      }));
    },
    [persist],
  );

  const setExperimentResult = useCallback(
    (experimentId: string, result: IngestionResult) => {
      const updatedAt = new Date().toISOString();
      persist((current) => ({
        ...current,
        experiments: current.experiments.map((experiment) => {
          if (experiment.id !== experimentId) return experiment;
          return {
            ...experiment,
            ingestionResult: result,
            status: statusFromIngestionResult(result) ?? experiment.status,
            updatedAt,
            unread: current.currentExperimentId !== experimentId,
          };
        }),
      }));
    },
    [persist],
  );

  const reviseExperimentRequest = useCallback(
    (experimentId: string, query: string) => {
      const updatedAt = new Date().toISOString();
      persist((current) => ({
        ...current,
        experiments: current.experiments.map((experiment) =>
          experiment.id === experimentId
            ? {
                ...experiment,
                query,
                status: "draft",
                ingestionResult: null,
                updatedAt,
                unread: false,
              }
            : experiment,
        ),
      }));
    },
    [persist],
  );

  const markExperimentRead = useCallback(
    (experimentId: string) => {
      persist((current) => ({
        ...current,
        experiments: current.experiments.map((experiment) =>
          experiment.id === experimentId ? { ...experiment, unread: false } : experiment,
        ),
      }));
    },
    [persist],
  );

  const setCurrentExperiment = useCallback(
    (experimentId: string | null) => {
      persist((current) => ({ ...current, currentExperimentId: experimentId }));
    },
    [persist],
  );

  const linkExperimentTrial = useCallback(
    (experimentId: string, trialId: string) => {
      const updatedAt = new Date().toISOString();
      persist((current) => ({
        ...current,
        experiments: current.experiments.map((experiment) =>
          experiment.id === experimentId
            ? { ...experiment, trialId, status: "active", updatedAt, unread: false }
            : experiment,
        ),
      }));
    },
    [persist],
  );

  const setProtocolIngestionResult = useCallback(
    (result: IngestionResult | null, experimentId: string | null = null) => {
      setIngestionResult(result);
      setProtocolExperimentId(result ? experimentId : null);
    },
    [],
  );

  const value = useMemo(
    () => ({
      state,
      setTrial,
      addObservation,
      completeTrial,
      updateSettings,
      restoreAll,
      createExperiment,
      appendExperimentMessage,
      setExperimentStatus,
      setExperimentResult,
      reviseExperimentRequest,
      markExperimentRead,
      setCurrentExperiment,
      linkExperimentTrial,
      setIngestionResult: setProtocolIngestionResult,
      ingestionResult,
      protocolExperimentId,
      clearAll,
    }),
    [
      state,
      setTrial,
      addObservation,
      completeTrial,
      updateSettings,
      restoreAll,
      createExperiment,
      appendExperimentMessage,
      setExperimentStatus,
      setExperimentResult,
      reviseExperimentRequest,
      markExperimentRead,
      setCurrentExperiment,
      linkExperimentTrial,
      setProtocolIngestionResult,
      ingestionResult,
      protocolExperimentId,
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
