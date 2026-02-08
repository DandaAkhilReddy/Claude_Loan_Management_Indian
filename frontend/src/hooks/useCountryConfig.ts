import { useCountryStore } from "../store/countryStore";
import { COUNTRY_CONFIGS, type CountryConfig } from "../lib/countryConfig";

export function useCountryConfig(): CountryConfig {
  const { country } = useCountryStore();
  return COUNTRY_CONFIGS[country];
}
