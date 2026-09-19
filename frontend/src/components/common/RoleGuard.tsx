import { useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/context/AuthContext";
import type { Role } from "@/data/mock/mockData";
import { LoadingState } from "@/components/common/States";

/**
 * Robust Frontend route protection that handles client-side hydration and safe navigation.
 */
export function RoleGuard({
  allow,
  redirectTo,
  children,
}: {
  allow: Role[];
  redirectTo: string;
  children: React.ReactNode;
}) {
  const { user, initializing } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!initializing) {
      if (!user) {
        navigate({ to: redirectTo, replace: true });
      } else if (!allow.includes(user.role)) {
        const fallback = user.role === "ADMIN" ? "/admin/dashboard" : "/crlr/dashboard";
        navigate({ to: fallback, replace: true });
      }
    }
  }, [user, initializing, allow, redirectTo, navigate]);

  if (initializing || !user || !allow.includes(user.role)) {
    return (
      <div className="mx-auto max-w-md p-8">
        <LoadingState rows={3} label="Checking access..." />
      </div>
    );
  }

  return <>{children}</>;
}
