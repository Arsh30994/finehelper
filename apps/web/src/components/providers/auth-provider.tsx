"use client";

import {
  createContext,
  startTransition,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { clearSession, getToken, me as fetchMe } from "@/api";
import type { Me } from "@/types";

type AuthStatus = "loading" | "authenticated" | "anonymous";

type AuthContextValue = {
  status: AuthStatus;
  me: Me | null;
  refresh: () => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [me, setMe] = useState<Me | null>(null);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      startTransition(() => {
        setMe(null);
        setStatus("anonymous");
      });
      return;
    }
    try {
      const data = await fetchMe();
      startTransition(() => {
        setMe(data);
        setStatus("authenticated");
      });
    } catch {
      clearSession();
      startTransition(() => {
        setMe(null);
        setStatus("anonymous");
      });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signOut = useCallback(() => {
    clearSession();
    startTransition(() => {
      setMe(null);
      setStatus("anonymous");
    });
    router.replace("/");
  }, [router]);

  return (
    <AuthContext.Provider value={{ status, me, refresh, signOut }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
