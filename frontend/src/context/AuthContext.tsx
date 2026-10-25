import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { AuthUser } from "@/data/mock/mockData";
import * as authService from "@/services/authService";

interface AuthContextValue {
  user: AuthUser | null;
  initializing: boolean;
  signIn: (email: string, password: string, portal: "ADMIN" | "CRLR" | "MENTOR") => Promise<AuthUser>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    let active = true;
    const persistedUser = authService.readPersistedUser();
    setUser(persistedUser);

    const handleUnauthorized = () => {
      authService.logout();
      setUser(null);
    };

    window.addEventListener("fams:unauthorized", handleUnauthorized);
    if (persistedUser) {
      authService.validateSession().catch((error: unknown) => {
        if (active && error instanceof Error && "status" in error && error.status === 401) {
          setUser(null);
        }
      }).finally(() => {
        if (active) setInitializing(false);
      });
    } else {
      setInitializing(false);
    }
    return () => {
      active = false;
      window.removeEventListener("fams:unauthorized", handleUnauthorized);
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      initializing,
      signIn: async (email, password, portal) => {
        const signedIn = await authService.login(email, password, portal);
        authService.persistUser(signedIn);
        setUser(signedIn);
        return signedIn;
      },
      signOut: async () => {
        await authService.logout();
        setUser(null);
      },
    }),
    [user, initializing],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
