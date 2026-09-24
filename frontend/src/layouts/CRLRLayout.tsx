import { useState, type ReactNode } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Calendar,
  ClipboardCheck,
  Bell,
  LogOut,
  Menu,
  GraduationCap,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { RoleGuard } from "@/components/common/RoleGuard";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/crlr/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/crlr/timetable", label: "Timetable", icon: Calendar },
  { to: "/crlr/attendance", label: "Attendance", icon: ClipboardCheck },
  { to: "/crlr/notifications", label: "Alerts", icon: Bell },
] as const;

export function CRLRLayout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const handleSignOut = async () => {
    await signOut();
    navigate({ to: "/auth/login", replace: true });
  };

  const nav = (
    <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
      {NAV_ITEMS.map((item) => (
        <Link
          key={item.to}
          to={item.to}
          onClick={() => setOpen(false)}
          className={cn(
            "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            pathname === item.to && "bg-sidebar-accent text-sidebar-accent-foreground font-semibold",
          )}
        >
          <item.icon className="size-4 shrink-0" />
          <span className="truncate">{item.label}</span>
        </Link>
      ))}
    </nav>
  );

  return (
    <RoleGuard allow={["CR", "LR"]} redirectTo="/auth/login">
      <div className="flex h-screen w-full overflow-hidden bg-background">
        {/* Sticky Left Navigation Sidebar */}
        <aside className="hidden h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex sticky top-0">
          <div className="flex shrink-0 items-center gap-2 border-b border-sidebar-border px-4 py-4">
            <GraduationCap className="size-6 text-sidebar-primary" />
            <span className="text-sm font-semibold text-sidebar-foreground">
              Faculty Attendance Monitor
            </span>
          </div>
          {nav}
          <div className="shrink-0 border-t border-sidebar-border p-3">
            <button
              onClick={handleSignOut}
              className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            >
              <LogOut className="size-4" /> Logout
            </button>
          </div>
        </aside>

        {/* Mobile Drawer */}
        {open ? (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div
              className="absolute inset-0 bg-foreground/40"
              onClick={() => setOpen(false)}
              aria-hidden
            />
            <aside className="absolute inset-y-0 left-0 flex w-64 flex-col bg-sidebar">
              <div className="flex shrink-0 items-center justify-between border-b border-sidebar-border px-4 py-4">
                <span className="text-sm font-semibold text-sidebar-foreground">CR / LR Menu</span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setOpen(false)}
                  aria-label="Close menu"
                  className="text-sidebar-foreground hover:bg-sidebar-accent"
                >
                  <X className="size-5" />
                </Button>
              </div>
              {nav}
              <div className="shrink-0 border-t border-sidebar-border p-3">
                <button
                  onClick={handleSignOut}
                  className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-sidebar-foreground/80 hover:bg-sidebar-accent"
                >
                  <LogOut className="size-4" /> Logout
                </button>
              </div>
            </aside>
          </div>
        ) : null}

        {/* Main Content Area - Scrolls Independently */}
        <div className="flex min-w-0 flex-1 flex-col h-screen overflow-hidden">
          <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-card px-4">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="size-5" />
            </Button>
            <span className="truncate text-sm font-semibold">CR / LR Portal</span>
            <div className="ml-auto flex min-w-0 items-center gap-3">
              <NotificationBell />
              <div className="hidden min-w-0 text-right sm:block">
                <p className="truncate text-xs font-semibold">{user?.name}</p>
                <p className="truncate text-[10px] text-muted-foreground">
                  {user?.role} · {user?.year} · Section {user?.section}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={handleSignOut}>
                <LogOut className="size-4" /> Logout
              </Button>
            </div>
          </header>
          <main className="min-w-0 flex-1 overflow-y-auto space-y-6 p-4 sm:p-6">{children}</main>
        </div>
      </div>
    </RoleGuard>
  );
}
