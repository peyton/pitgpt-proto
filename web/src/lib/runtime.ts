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
  return invoke<T>(command, args);
}
