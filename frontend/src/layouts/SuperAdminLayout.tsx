import { useState, type ReactNode } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Building2,
  GitBranch,
  UserCheck,
  Menu,
  ShieldAlert,
  X,
  Crown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/context/AuthContext";
import { RoleGuard } from "@/components/common/RoleGuard";
import { LogoutConfirmation } from "@/components/common/LogoutConfirmation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/super-admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/super-admin/sites", label: "Sites", icon: Building2 },
  { to: "/super-admin/branches", label: "Branches Management", icon: GitBranch },
  { to: "/super-admin/hods", label: "HOD Management", icon: UserCheck },
] as const;

export function SuperAdminLayout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const handleSignOut = async () => {
    await signOut();
    navigate({ to: "/super-admin/login", replace: true });
  };

  const nav = (
    <nav className="flex flex-1 flex-col gap-1.5 overflow-y-auto p-3">
      <div className="px-3 py-1 text-[11px] font-semibold tracking-wider text-sidebar-foreground/60 uppercase">
        Administration
      </div>
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.to || pathname.startsWith(item.to + "/");
        return (
          <Link
            key={item.to}
            to={item.to}
            onClick={() => setOpen(false)}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              isActive
                ? "bg-indigo-600 text-white shadow-sm font-semibold hover:bg-indigo-700"
                : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            )}
          >
            <item.icon className={cn("size-4 shrink-0", isActive ? "text-white" : "text-sidebar-foreground/70")} />
            <span className="truncate">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );

  return (
    <RoleGuard allow={["SUPER_ADMIN"]} redirectTo="/super-admin/login">
      <div className="flex h-screen w-full overflow-hidden bg-background">
        {/* Sticky Left Navigation Sidebar */}
        <aside className="hidden h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex sticky top-0">
          <div className="flex shrink-0 items-center gap-2.5 border-b border-sidebar-border px-4 py-4 bg-gradient-to-r from-indigo-950/40 to-transparent">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white shadow">
              <Crown className="size-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight text-sidebar-foreground">
                Super Admin
              </span>
              <span className="text-[11px] text-indigo-500 font-medium">Multi-Branch System</span>
            </div>
          </div>

          {nav}

          <div className="shrink-0 border-t border-sidebar-border p-3">
            <div className="mb-2 rounded-lg bg-sidebar-accent/50 p-2.5">
              <div className="flex items-center gap-2">
                <ShieldAlert className="size-4 text-indigo-500 shrink-0" />
                <span className="text-xs font-semibold text-sidebar-foreground truncate">
                  Master Authority
                </span>
              </div>
              <p className="mt-1 text-[11px] text-sidebar-foreground/60 leading-tight">
                Global multi-branch &amp; HOD management
              </p>
            </div>
            <LogoutConfirmation onConfirm={handleSignOut} compact />
          </div>
        </aside>

        {/* Mobile Drawer */}
        {open ? (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div
              className="absolute inset-0 bg-foreground/40 backdrop-blur-xs"
              onClick={() => setOpen(false)}
              aria-hidden
            />
            <aside className="absolute inset-y-0 left-0 flex w-64 flex-col bg-sidebar shadow-2xl">
              <div className="flex shrink-0 items-center justify-between border-b border-sidebar-border px-4 py-4">
                <div className="flex items-center gap-2">
                  <Crown className="size-5 text-indigo-600" />
                  <span className="text-sm font-bold text-sidebar-foreground">Super Admin</span>
                </div>
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
                <LogoutConfirmation onConfirm={handleSignOut} compact />
              </div>
            </aside>
          </div>
        ) : null}

        {/* Main Content Area */}
        <div className="flex min-w-0 flex-1 flex-col h-screen overflow-hidden">
          <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-card px-4 shadow-xs">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="size-5" />
            </Button>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-300 font-semibold text-[11px] gap-1">
                <Crown className="size-3" /> Super Admin Portal
              </Badge>
            </div>
            <div className="ml-auto flex min-w-0 items-center gap-3">
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-semibold text-foreground truncate max-w-[200px]">
                  {user?.name || "Super Admin"}
                </span>
                <span className="text-[11px] text-muted-foreground truncate max-w-[200px]">
                  {user?.email || "superadmin@fams.edu"}
                </span>
              </div>
              <LogoutConfirmation onConfirm={handleSignOut} />
            </div>
          </header>
          <main className="min-w-0 flex-1 overflow-y-auto space-y-6 p-4 sm:p-6 lg:p-8 bg-slate-50/60 dark:bg-slate-950/30">
            {children}
          </main>
        </div>
      </div>
    </RoleGuard>
  );
}
