import { useState, type FormEvent } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { GraduationCap, LogIn, Lock, UserCheck } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/mentor/login")({
  head: () => ({
    meta: [
      { title: "Mentor Login — Session Monitoring System" },
      { name: "description", content: "Sign in to access your assigned student absentees and attendance analytics." },
    ],
  }),
  component: MentorLoginPage,
});

function MentorLoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      toast.error("Please enter your Mentor ID or Email and password.");
      return;
    }

    setLoading(true);
    try {
      await signIn(identifier.trim(), password, "MENTOR");
      toast.success("Welcome, Mentor!");
      navigate({ to: "/mentor/absentees", replace: true });
    } catch (err: any) {
      toast.error(err.message || "Invalid credentials or unauthorized account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4 dark:bg-slate-950">
      <Card className="w-full max-w-md shadow-lg border-slate-200 dark:border-slate-800">
        <CardHeader className="text-center space-y-2 pb-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950/60">
            <UserCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
          </div>
          <CardTitle className="text-xl font-bold text-slate-900 dark:text-white">
            Mentor Portal Sign In
          </CardTitle>
          <CardDescription className="text-xs text-slate-500">
            Enter your Mentor ID or Email to view student absentees and analytics.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="identifier">Mentor ID or Email</Label>
              <div className="relative">
                <GraduationCap className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  id="identifier"
                  type="text"
                  placeholder="e.g. M101 or mentor@example.com"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>

            <Button type="submit" disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium">
              <LogIn className="mr-2 h-4 w-4" />
              {loading ? "Signing in..." : "Sign In to Mentor Portal"}
            </Button>
          </form>

          <div className="mt-6 border-t border-slate-100 pt-4 text-center text-xs text-slate-500 dark:border-slate-800 flex justify-center gap-4">
            <a href="/admin/login" className="hover:text-indigo-600 underline">Admin Login</a>
            <span>•</span>
            <a href="/auth/login" className="hover:text-indigo-600 underline">CR/LR Login</a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
