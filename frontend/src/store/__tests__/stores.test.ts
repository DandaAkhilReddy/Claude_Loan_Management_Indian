/// <reference types="vitest/globals" />
import type { User } from "firebase/auth";

// Mock the i18n module used by languageStore
vi.mock("../../lib/i18n", () => ({
  default: {
    changeLanguage: vi.fn(),
  },
}));

import { useAuthStore } from "../authStore";
import { useLanguageStore } from "../languageStore";
import { useCountryStore } from "../countryStore";
import { useUIStore } from "../uiStore";
import { useToastStore } from "../toastStore";
import i18n from "../../lib/i18n";

// ---------------------------------------------------------------------------
// Reset every store + localStorage before each test to guarantee isolation
// ---------------------------------------------------------------------------
beforeEach(() => {
  localStorage.clear();

  useAuthStore.setState({ user: null, loading: true });
  useLanguageStore.setState({ language: "en" });
  useCountryStore.setState({ country: "IN" });
  useUIStore.setState({ sidebarOpen: true });
  useToastStore.setState({ toasts: [] });

  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// authStore
// ---------------------------------------------------------------------------
describe("authStore", () => {
  it("setUser updates user and sets loading to false", () => {
    const fakeUser = { uid: "abc123" } as unknown as User;
    useAuthStore.getState().setUser(fakeUser);

    const state = useAuthStore.getState();
    expect(state.user).not.toBeNull();
    expect(state.user).toBe(fakeUser);
    expect(state.loading).toBe(false);
  });

  it("setLoading updates loading", () => {
    // Initial loading is true (from reset). Set to false, then back to true.
    useAuthStore.getState().setLoading(false);
    expect(useAuthStore.getState().loading).toBe(false);

    useAuthStore.getState().setLoading(true);
    expect(useAuthStore.getState().loading).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// languageStore
// ---------------------------------------------------------------------------
describe("languageStore", () => {
  it("default language is en", () => {
    expect(useLanguageStore.getState().language).toBe("en");
  });

  it("setLanguage updates state and localStorage", () => {
    useLanguageStore.getState().setLanguage("hi");

    expect(useLanguageStore.getState().language).toBe("hi");
    expect(localStorage.getItem("language")).toBe("hi");
  });

  it("setLanguage calls i18n.changeLanguage", () => {
    useLanguageStore.getState().setLanguage("te");

    expect(i18n.changeLanguage).toHaveBeenCalledWith("te");
  });
});

// ---------------------------------------------------------------------------
// countryStore
// ---------------------------------------------------------------------------
describe("countryStore", () => {
  it("default country is IN", () => {
    expect(useCountryStore.getState().country).toBe("IN");
  });

  it("setCountry updates state and localStorage", () => {
    useCountryStore.getState().setCountry("US");

    expect(useCountryStore.getState().country).toBe("US");
    expect(localStorage.getItem("country")).toBe("US");
  });
});

// ---------------------------------------------------------------------------
// uiStore
// ---------------------------------------------------------------------------
describe("uiStore", () => {
  it("default sidebarOpen is true", () => {
    expect(useUIStore.getState().sidebarOpen).toBe(true);
  });

  it("toggleSidebar flips sidebarOpen", () => {
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarOpen).toBe(false);

    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarOpen).toBe(true);
  });

  it("setSidebarOpen sets directly", () => {
    useUIStore.getState().setSidebarOpen(false);
    expect(useUIStore.getState().sidebarOpen).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// toastStore
// ---------------------------------------------------------------------------
describe("toastStore", () => {
  it("addToast adds toast with generated id", () => {
    useToastStore.getState().addToast({ type: "success", message: "ok" });

    const { toasts } = useToastStore.getState();
    expect(toasts).toHaveLength(1);
    expect(typeof toasts[0].id).toBe("string");
    expect(toasts[0].id.length).toBeGreaterThan(0);
    expect(toasts[0].type).toBe("success");
    expect(toasts[0].message).toBe("ok");
  });

  it("removeToast removes by id", () => {
    useToastStore.getState().addToast({ type: "error", message: "fail" });

    const id = useToastStore.getState().toasts[0].id;
    expect(useToastStore.getState().toasts).toHaveLength(1);

    useToastStore.getState().removeToast(id);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });
});
