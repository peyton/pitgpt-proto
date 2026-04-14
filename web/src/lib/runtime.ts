export type RuntimeMode = "web" | "tauri-desktop" | "tauri-ios";

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

export function getRuntimeMode(): RuntimeMode {
  if (!isTauriRuntime()) return "web";
  const userAgent = typeof navigator === "undefined" ? "" : navigator.userAgent;
  if (/iPad|iPhone|iPod/.test(userAgent)) return "tauri-ios";
  return "tauri-desktop";
}

export function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && Boolean(window.__TAURI_INTERNALS__);
}

export async function invokeNative<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import("@tauri-apps/api/core");
  try {
    return await invoke<T>(command, args);
  } catch (error) {
    throw normalizeNativeError(error);
  }
}

function normalizeNativeError(error: unknown): Error {
  if (error instanceof Error) return error;
  if (typeof error === "string" && error.trim()) return new Error(error);
  return new Error("Native command failed.");
}
