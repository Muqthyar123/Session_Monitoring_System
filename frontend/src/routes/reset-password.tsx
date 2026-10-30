import { useEffect, useState, type FormEvent } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Eye, EyeOff, Loader2, LockKeyhole } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { resetPassword, verifyPasswordResetToken } from "@/services/authService";
import type { Role } from "@/data/mock/mockData";

export const Route = createFileRoute("/reset-password")({ validateSearch: (search: Record<string, unknown>) => ({ token: typeof search.token === "string" ? search.token : "" }), component: ResetPasswordPage });

function ResetPasswordPage() {
  const { token } = Route.useSearch();
  const navigate = useNavigate();
  const [validating, setValidating] = useState(true);
  const [valid, setValid] = useState(false);
  const [role, setRole] = useState<Role>("CR");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);
  useEffect(() => { let active = true; verifyPasswordResetToken(token).then((data) => { if (active) { setRole(data.role); setValid(data.valid); } }).catch(() => { if (active) setValid(false); }).finally(() => { if (active) setValidating(false); }); return () => { active = false; }; }, [token]);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!/^(?=.*[A-Za-z])(?=.*\d).{8,12}$/.test(password)) { toast.error("Password must be 8–12 characters and include a letter and a number."); return; }
    if (password !== confirm) { toast.error("Passwords do not match."); return; }
    setSaving(true);
    try { await resetPassword(token, password); toast.success("Password updated. Sign in with your new password."); navigate({ to: role === "ADMIN" ? "/admin/login" : role === "MENTOR" ? "/mentor/login" : "/auth/login", replace: true }); }
    catch (error) { toast.error(error instanceof Error ? error.message : "Password reset failed."); }
    finally { setSaving(false); }
  };
  return <div className="flex min-h-screen items-center justify-center bg-background px-4 py-10"><Card className="w-full max-w-md"><CardHeader className="text-center"><div className="mx-auto grid size-12 place-items-center rounded-xl bg-primary text-primary-foreground"><LockKeyhole className="size-6" /></div><CardTitle>Reset Password</CardTitle><CardDescription>Choose a new password for your account.</CardDescription></CardHeader><CardContent>{validating ? <div className="flex justify-center p-6"><Loader2 className="size-5 animate-spin" /></div> : !valid ? <div className="space-y-4 text-center"><p className="text-sm text-destructive">This password reset link is invalid or has expired.</p><Link to="/forgot-password" className="text-sm font-medium text-primary underline">Request a new link</Link></div> : <form onSubmit={submit} className="space-y-4"><div className="space-y-1.5"><Label htmlFor="new-password">New Password</Label><div className="relative"><Input id="new-password" type={show ? "text" : "password"} autoComplete="new-password" minLength={8} maxLength={12} required value={password} onChange={(e) => setPassword(e.target.value)} className="pr-10" /><button type="button" aria-label={show ? "Hide password" : "Show password"} onClick={() => setShow(!show)} className="absolute inset-y-0 right-0 grid w-10 place-items-center text-muted-foreground">{show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}</button></div><p className="text-xs text-muted-foreground">8–12 characters, including at least one letter and one number.</p></div><div className="space-y-1.5"><Label htmlFor="confirm-password">Confirm New Password</Label><Input id="confirm-password" type={show ? "text" : "password"} autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} /></div><Button className="w-full" type="submit" disabled={saving}>{saving && <Loader2 className="size-4 animate-spin" />}Reset Password</Button></form>}</CardContent></Card></div>;
}
