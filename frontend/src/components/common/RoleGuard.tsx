import { useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/context/AuthContext";
import type { Role } from "@/data/mock/mockData";
import { LoadingState } from "@/components/common/States";

/**
 * Frontend-only route protection. Real authorization will also be enforced
 * by the backend.
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
  const allowed = user ? allow.includes(user.role) : false;

  useEffect(() => {
    if (initializing) return;
    if (!user) {
      navigate({ to: redirectTo, replace: true });
      return;
    }
    if (!allowed) {
      navigate({ to: user.role === "ADMIN" ? "/admin/dashboard" : "/crlr/dashboard", replace: true });
    }
  }, [initializing, user, allowed, navigate, redirectTo]);

  if (initializing || !user || !allowed) {
    return (
      <div className="mx-auto max-w-md p-8">
        <LoadingState rows={3} label="Checking access..." />
      </div>
    );
  }

  return <>{children}</>;
}
