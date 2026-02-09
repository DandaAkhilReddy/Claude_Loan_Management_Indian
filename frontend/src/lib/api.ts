// Auth paused — no token attachment, no 401 redirect
import axios from "axios";
import { useToastStore } from "../store/toastStore";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Handle errors — toast notifications (no 401 redirect)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const { addToast } = useToastStore.getState();

    if (error.response) {
      const status = error.response.status;
      if (status === 429) {
        addToast({ type: "warning", message: "Too many requests. Please wait a moment." });
      } else if (status >= 500) {
        addToast({ type: "error", message: "Server error. Please try again later." });
      }
    } else {
      addToast({ type: "error", message: "Network error. Check your connection." });
    }

    return Promise.reject(error);
  }
);

export default api;
