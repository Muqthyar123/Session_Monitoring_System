import { useState, type FormEvent } from "react";
import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { Eye, EyeOff, GraduationCap, Loader2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";
import { MOCK_DEMO_CREDENTIALS } from "@/data/mock/mockData";

export const Route = createFileRoute("/admin/login")({
  head: () => ({
    meta: [
      { title: "Admin Login — Faculty Attendance Monitor" },
      { name: "description", content: "Administrator sign-in for the faculty attendance and session monitoring system." },
      { property: "og:title", content: "Admin Login — Faculty Attendance Monitor" },
      { property: "og:description", content: "Administrator sign-in for the faculty attendance monitoring system." },
    ],
  }),
  component: AdminLoginPage,
});

function AdminLoginPage() {
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
      await signIn(email, password, "ADMIN");
      navigate({ to: "/admin/dashboard", replace: true });
    } catch (error) {
      setErrors({ form: error instanceof Error ? error.message : "Login failed." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-10">
      <Card className="w-full max-w-md">
        <CardHeader className="items-center text-center">
          <span className="grid size-12 place-items-center rounded-xl bg-primary text-primary-foreground">
            <GraduationCap className="size-6" />
          </span>
          <CardTitle className="text-xl">Faculty Attendance Monitor</CardTitle>
          <CardDescription className="flex items-center justify-center gap-1.5 font-medium text-foreground">
            <ShieldCheck className="size-4" /> Admin Login
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="admin-email">Email / Username</Label>
              <Input
                id="admin-email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@example.com"
                aria-invalid={Boolean(errors.email)}
              />
              {errors.email ? <p className="text-xs text-destructive">{errors.email}</p> : null}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="admin-password">Password</Label>
              <div className="relative">
                <Input
                  id="admin-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pr-10"
                  aria-invalid={Boolean(errors.password)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 grid w-10 place-items-center text-muted-foreground"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {errors.password ? (
                <p className="text-xs text-destructive">{errors.password}</p>
              ) : null}
            </div>

            {errors.form ? (
              <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {errors.form}
              </p>
            ) : null}

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? <Loader2 className="size-4 animate-spin" /> : null}
              Login
            </Button>
          </form>

          <div className="mt-6 rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
            <p className="font-medium text-foreground">System Administrator Account</p>
            <p>
              {MOCK_DEMO_CREDENTIALS.admin.email} / {MOCK_DEMO_CREDENTIALS.admin.password}
            </p>
          </div>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            Are you a CR/LR?{" "}
            <Link to="/auth/login" className="font-medium text-primary underline underline-offset-4">
              CR / LR Login
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
