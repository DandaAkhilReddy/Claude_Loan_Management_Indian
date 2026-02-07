import { create } from "zustand";
import i18n from "../lib/i18n";

interface LanguageState {
  language: string;
  setLanguage: (lang: string) => void;
}

export const useLanguageStore = create<LanguageState>((set) => ({
  language: localStorage.getItem("language") || "en",
  setLanguage: (lang: string) => {
    localStorage.setItem("language", lang);
    i18n.changeLanguage(lang);
    set({ language: lang });
  },
}));
