import { useEffect } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { auth, signInWithPopup, googleProvider, signInWithPhoneNumber, RecaptchaVerifier } from "../lib/firebase";
import { useAuthStore } from "../store/authStore";
import api from "../lib/api";

export function useAuth() {
  const { user, loading, setUser, setLoading } = useAuthStore();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser) {
        try {
          const token = await firebaseUser.getIdToken();
          await api.post("/api/auth/verify-token", null, {
            headers: { Authorization: `Bearer ${token}` },
          });
        } catch {
          // Token verification failed — user will need to re-login
        }
      }
    });
    return unsubscribe;
  }, [setUser]);

  const loginWithGoogle = async () => {
    setLoading(true);
    try {
      await signInWithPopup(auth, googleProvider);
    } finally {
      setLoading(false);
    }
  };

  const loginWithPhone = async (phoneNumber: string, recaptchaContainer: string) => {
    const recaptchaVerifier = new RecaptchaVerifier(auth, recaptchaContainer, {
      size: "normal",
    });
    const confirmationResult = await signInWithPhoneNumber(auth, phoneNumber, recaptchaVerifier);
    return confirmationResult;
  };

  const logout = async () => {
    await auth.signOut();
    setUser(null);
  };

  return { user, loading, loginWithGoogle, loginWithPhone, logout };
}
