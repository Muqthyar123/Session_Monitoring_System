import { useState, type FormEvent } from "react";
import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { Eye, EyeOff, Crown, Loader2, ShieldAlert, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";

export const Route = createFileRoute("/super-admin/login")({
  head: () => ({
    meta: [
      { title: "Super Admin Login — Faculty Attendance Monitor" },
      { name: "description", content: "Master Administrator sign-in for multi-branch and campus management." },
      { property: "og:title", content: "Super Admin Login — Faculty Attendance Monitor" },
      { property: "og:description", content: "Master Administrator sign-in for multi-branch and campus management." },
    ],
  }),
  component: SuperAdminLoginPage,
});

function SuperAdminLoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string; form?: string }>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const nextErrors: typeof errors = {};
    if (!email.trim()) nextErrors.email = "Email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
      nextErrors.email = "Enter a valid email address.";
    if (!password) nextErrors.password = "Password is required.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await signIn(email, password, "SUPER_ADMIN");
      navigate({ to: "/super-admin/dashboard", replace: true });
    } catch (error) {
      setErrors({ form: error instanceof Error ? error.message : "Super Admin login failed." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10 relative overflow-hidden">
      {/* Decorative background glows */}
      <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-violet-600/20 blur-3xl pointer-events-none" />

      <div className="w-full max-w-md z-10 space-y-4">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="size-3.5" /> Back to portal selection
        </Link>

        <Card className="w-full border-slate-800 bg-slate-900/90 text-white shadow-2xl backdrop-blur-xl">
          <CardHeader className="items-center text-center pb-4">
            <span className="grid size-14 place-items-center rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-500/30">
              <Crown className="size-7" />
            </span>
            <div className="mt-3 space-y-1">
              <CardTitle className="text-2xl font-black tracking-tight text-white">
                Super Admin Portal
              </CardTitle>
              <CardDescription className="text-slate-400 text-xs font-medium">
                Multi-Branch &amp; Institutional Governance
              </CardDescription>
            </div>
            <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-0.5 text-[11px] font-medium text-indigo-300">
              <ShieldAlert className="size-3" /> Master Access Required
            </div>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit} noValidate>
              <div className="space-y-1.5">
                <Label htmlFor="superadmin-email" className="text-slate-300 text-xs font-semibold">
                  Email Address
                </Label>
                <Input
                  id="superadmin-email"
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="superadmin@fams.edu"
                  className="border-slate-800 bg-slate-950/60 text-white placeholder:text-slate-600 focus-visible:ring-indigo-500"
                  aria-invalid={Boolean(errors.email)}
                />
                {errors.email ? <p className="text-xs text-rose-400">{errors.email}</p> : null}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="superadmin-password" className="text-slate-300 text-xs font-semibold">
                  Password
                </Label>
                <div className="relative">
                  <Input
                    id="superadmin-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="border-slate-800 bg-slate-950/60 pr-10 text-white placeholder:text-slate-600 focus-visible:ring-indigo-500"
                    aria-invalid={Boolean(errors.password)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute inset-y-0 right-0 grid w-10 place-items-center text-slate-400 hover:text-slate-200 transition-colors"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
                {errors.password ? <p className="text-xs text-rose-400">{errors.password}</p> : null}
              </div>

              {errors.form ? (
                <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
                  {errors.form}
                </div>
              ) : null}

              <Button
                type="submit"
                disabled={submitting}
                className="w-full bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-semibold shadow-md shadow-indigo-600/25 hover:from-indigo-500 hover:to-violet-500 transition-all cursor-pointer"
              >
                {submitting ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="size-4 animate-spin" /> Authenticating...
                  </span>
                ) : (
                  "Sign In as Super Admin"
                )}
              </Button>
            </form>

            <div className="mt-6 border-t border-slate-800 pt-4 text-center">
              <p className="text-[11px] text-slate-500">
                Unauthorized access to the Super Admin portal is strictly monitored and logged.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
