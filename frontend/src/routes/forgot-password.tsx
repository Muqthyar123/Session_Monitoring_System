import { useRef, useState, type FormEvent } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Loader2, Mail } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { requestPasswordReset } from "@/services/authService";

export const Route = createFileRoute("/forgot-password")({ component: ForgotPasswordPage });

function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const requestInFlight = useRef(false);
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (requestInFlight.current || loading || sent) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) { toast.error("Enter a valid account email address."); return; }
    requestInFlight.current = true;
    setLoading(true);
    setErrorMessage("");
    try { await requestPasswordReset(email.trim()); setSent(true); }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : "Could not request a reset link."); }
    finally { requestInFlight.current = false; setLoading(false); }
  };
  return <div className="flex min-h-screen items-center justify-center bg-background px-4 py-10"><Card className="w-full max-w-md"><CardHeader className="text-center"><div className="mx-auto grid size-12 place-items-center rounded-xl bg-primary text-primary-foreground"><Mail className="size-6" /></div><CardTitle>Forgot Password?</CardTitle><CardDescription>Enter the email address registered to your account.</CardDescription></CardHeader><CardContent>{sent ? <div className="space-y-4 text-center"><p className="rounded-md bg-emerald-500/10 p-3 text-sm">If an account exists with this email address, a password reset link has been sent.</p><Link to="/auth/login" className="text-sm font-medium text-primary underline">Return to login</Link></div> : <form onSubmit={handleSubmit} className="space-y-4"><div className="space-y-1.5"><Label htmlFor="reset-email">Email</Label><Input id="reset-email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>{errorMessage && <p role="alert" className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{errorMessage}</p>}<Button className="w-full" type="submit" disabled={loading}>{loading && <Loader2 className="size-4 animate-spin" />}{loading ? "Sending..." : "Send Reset Link"}</Button><div className="text-center"><Link to="/auth/login" className="text-sm text-muted-foreground underline">Back to login</Link></div></form>}</CardContent></Card></div>;
}
