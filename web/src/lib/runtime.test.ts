import { afterEach, describe, expect, it, vi } from "vitest";
import { getRuntimeMode, isTauriRuntime } from "./runtime";

describe("runtime", () => {
  afterEach(() => {
    Reflect.deleteProperty(globalThis, "window");
    vi.unstubAllGlobals();
  });

  it("detects browser mode by default", () => {
    expect(isTauriRuntime()).toBe(false);
    expect(getRuntimeMode()).toBe("web");
  });

  it("detects desktop tauri when the tauri bridge is present", () => {
    vi.stubGlobal("window", { __TAURI_INTERNALS__: {} });

    expect(isTauriRuntime()).toBe(true);
    expect(getRuntimeMode()).toBe("tauri-desktop");
  });

  it("detects ios tauri from user agent", () => {
    vi.stubGlobal("window", { __TAURI_INTERNALS__: {} });
    vi.stubGlobal("navigator", { userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)" });

    expect(getRuntimeMode()).toBe("tauri-ios");
  });
});
