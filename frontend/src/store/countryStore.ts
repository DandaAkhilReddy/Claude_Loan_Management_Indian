import { create } from "zustand";

export type CountryCode = "IN" | "US";

interface CountryState {
  country: CountryCode;
  setCountry: (country: CountryCode) => void;
}

export const useCountryStore = create<CountryState>((set) => ({
  country: (localStorage.getItem("country") as CountryCode) || "IN",
  setCountry: (country: CountryCode) => {
    localStorage.setItem("country", country);
    set({ country });
  },
}));
