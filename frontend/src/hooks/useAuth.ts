// Auth paused — fake user for testing, no Firebase calls
import { useEffect } from "react";
import { useAuthStore } from "../store/authStore";

export function useAuth() {
  const { user, loading, setUser, setLoading } = useAuthStore();

  useEffect(() => {
    setUser({ displayName: "Admin", email: "admin@test.com", uid: "dev-admin" } as any);
    setLoading(false);
  }, [setUser, setLoading]);

  return {
    user,
    loading,
    loginWithGoogle: async () => {},
    loginWithEmail: async (_email: string, _password: string) => {},
    signupWithEmail: async (_email: string, _password: string, _displayName: string) => {},
    resetPassword: async (_email: string) => {},
    logout: async () => {},
  };
}
