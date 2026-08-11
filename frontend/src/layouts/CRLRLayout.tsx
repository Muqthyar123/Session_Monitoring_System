import type { ReactNode } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, ClipboardCheck, BarChart3, Bell, LogOut, GraduationCap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { RoleGuard } from "@/components/common/RoleGuard";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/crlr/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/crlr/attendance", label: "Attendance", icon: ClipboardCheck },
  { to: "/crlr/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/crlr/notifications", label: "Alerts", icon: Bell },
] as const;

export function CRLRLayout({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const handleSignOut = async () => {
    await signOut();
    navigate({ to: "/auth/login", replace: true });
  };

  return (
    <RoleGuard allow={["CR", "LR"]} redirectTo="/auth/login">
      <div className="flex min-h-screen flex-col bg-background">
        <header className="sticky top-0 z-30 border-b border-border bg-card">
          <div className="mx-auto grid w-full max-w-4xl grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-3">
            <div className="flex min-w-0 items-center gap-2">
              <GraduationCap className="size-5 shrink-0 text-primary" />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{user?.name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {user?.role} · {user?.year} · Section {user?.section}
                </p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <NotificationBell />
              <Button variant="ghost" size="icon" onClick={handleSignOut} aria-label="Logout">
                <LogOut className="size-5" />
              </Button>
            </div>
          </div>
          <nav className="mx-auto flex w-full max-w-4xl gap-1 overflow-x-auto px-2 pb-2">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary",
                  pathname === item.to && "bg-secondary text-foreground",
                )}
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="mx-auto w-full max-w-4xl flex-1 space-y-6 p-4">{children}</main>
      </div>
    </RoleGuard>
  );
}
