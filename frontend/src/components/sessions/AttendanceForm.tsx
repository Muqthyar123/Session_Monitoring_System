import { useEffect, useState } from "react";
import { CheckCircle2, Clock, UserCheck, UserX } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { submitFacultyAttendance, submitSubstitute } from "@/services/sessionService";
import type { ClassSession } from "@/data/mock/mockData";

type Step = "choose" | "confirm-present" | "substitute-question" | "substitute-name";

function parseMinutes(tStr: string): number {
  if (!tStr) return 0;
  const parts = tStr.split(":");
  let h = parseInt(parts[0] || "0", 10);
  const m = parseInt(parts[1] || "0", 10);
  if (h < 8) h += 12;
  return h * 60 + m;
}

export function AttendanceForm({
  session,
  onSubmitted,
}: {
  session: ClassSession;
  onSubmitted: (updated: ClassSession) => void;
}) {
  const [step, setStep] = useState<Step>("choose");
  const [substituteName, setSubstituteName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);

  const answered = session.facultyResponse !== "Pending";

  useEffect(() => {
    if (answered) {
      setSecondsLeft(null);
      return;
    }

    const calculateRemaining = () => {
      const now = new Date();
      const parts = (session.startTime || "09:00").split(":");
      let sh = parseInt(parts[0] || "9", 10);
      const sm = parseInt(parts[1] || "0", 10);
      if (sh < 8) sh += 12;
      const startMs = new Date(now.getFullYear(), now.getMonth(), now.getDate(), sh, sm, 0).getTime();
      const windowEndMs = startMs + 600000; // 10 minutes (600 seconds)
      const diffSec = Math.floor((windowEndMs - Date.now()) / 1000);
      return diffSec;
    };

    setSecondsLeft(calculateRemaining());
    const interval = setInterval(() => {
      setSecondsLeft(calculateRemaining());
    }, 1000);

    return () => clearInterval(interval);
  }, [session.startTime, answered]);

  const formatTimer = (sec: number) => {
    if (sec <= 0) return "00:00 (10 Min Expired)";
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const run = async (action: () => Promise<ClassSession>) => {
    setSubmitting(true);
    try {
      const updated = await action();
      toast.success("Attendance response submitted successfully");
      onSubmitted(updated);
      setStep("choose");
      setIsEditing(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not submit your response.");
    } finally {
      setSubmitting(false);
    }
  };

  const sessionId = session.id || (session as any)._id || "";

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden dark:border-slate-800 dark:bg-slate-900 transition-all">
      {/* Top Header Bar */}
      <div className="bg-slate-100/90 px-5 py-3.5 border-b border-slate-200 dark:bg-slate-800/80 dark:border-slate-800 flex items-center justify-between">
        <h3 className="text-base font-bold text-slate-900 dark:text-white truncate">
          {session.period} — {session.subject}
        </h3>
        <StatusBadge
          status={
            answered
              ? session.facultyResponse
              : session.sessionStatus
          }
        />
      </div>

      {/* Card Details Body */}
      <div className="p-5 space-y-4">
        <div className="grid grid-cols-[160px_1fr] gap-y-2.5 text-sm">
          <span className="text-slate-500 dark:text-slate-400 font-medium">Subject:</span>
          <span className="text-slate-900 dark:text-white font-semibold truncate">{session.subject}</span>

          <span className="text-slate-500 dark:text-slate-400 font-medium">Assigned Faculty:</span>
          <span className="text-indigo-600 dark:text-indigo-400 font-bold truncate">
            {session.faculty || "Not Specified"}
          </span>

          <span className="text-slate-500 dark:text-slate-400 font-medium">Start Time:</span>
          <span className="text-slate-900 dark:text-white font-semibold">{session.startTime}</span>

          <span className="text-slate-500 dark:text-slate-400 font-medium">End Time:</span>
          <span className="text-slate-900 dark:text-white font-semibold">{session.endTime}</span>
        </div>

        {/* 10-Minute Live Countdown Timer Banner */}
        {(!answered || isEditing) ? (
          <div className="rounded-lg bg-amber-50/90 border border-amber-200/80 dark:bg-amber-950/40 dark:border-amber-900/60 p-3 text-xs font-semibold text-amber-900 dark:text-amber-200 flex items-center justify-between shadow-xs">
            <span className="flex items-center gap-2">
              <Clock className="size-4 text-amber-600 dark:text-amber-400 animate-pulse" />
              10-Minute Attendance Marking Window
            </span>
            <span className="font-mono text-sm font-bold bg-amber-200/70 dark:bg-amber-900/80 text-amber-950 dark:text-amber-100 px-2.5 py-1 rounded-md border border-amber-300 dark:border-amber-700">
              {secondsLeft !== null ? formatTimer(secondsLeft) : "10:00"}
            </span>
          </div>
        ) : null}

        {/* Card Footer Actions - Fully accessible for testing */}
        <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
          {answered && !isEditing ? (
            /* Completed & Marked Period -> Read-Only Badge + Re-mark Option */
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm font-medium">
              {session.facultyResponse === "Present" ? (
                <span className="inline-flex items-center gap-1.5 rounded-md bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                  <CheckCircle2 className="size-4" /> Attended (Faculty Present)
                </span>
              ) : session.facultyResponse === "Not Present" || session.facultyResponse === "Absent" ? (
                <span className="inline-flex items-center gap-1.5 rounded-md bg-rose-50 px-3 py-1.5 text-xs font-bold text-rose-700 dark:bg-rose-950/40 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
                  <UserX className="size-4" /> Not Attended (Faculty Absent)
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-md bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
                  <UserCheck className="size-4" /> Substitute: {session.substituteName || "Assigned"}
                </span>
              )}
              <div className="flex items-center gap-2 ml-auto">
                {session.responseTime ? (
                  <span className="text-xs text-slate-400">Responded: {session.responseTime}</span>
                ) : null}
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 text-xs text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950"
                  onClick={() => setIsEditing(true)}
                >
                  Change Response
                </Button>
              </div>
            </div>
          ) : step === "choose" ? (
            /* Active Class Period -> Interactive Present / Not Present Buttons */
            <div className="grid gap-3 sm:grid-cols-2">
              <Button
                size="md"
                onClick={() => setStep("confirm-present")}
                disabled={submitting}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
              >
                <CheckCircle2 className="size-4 mr-2" /> Faculty Present
              </Button>
              <Button
                size="md"
                variant="outline"
                onClick={() => setStep("substitute-question")}
                disabled={submitting}
                className="border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200"
              >
                <UserX className="size-4 mr-2 text-rose-500" /> Faculty Not Present
              </Button>
            </div>
          ) : step === "confirm-present" ? (
            <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-sm text-slate-800 dark:text-slate-200">
                Confirm that assigned faculty{" "}
                <span className="font-bold text-slate-900 dark:text-white">
                  {session.faculty ? `${session.faculty} (${session.subject})` : session.subject}
                </span>{" "}
                is present for this period?
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() => run(() => submitFacultyAttendance(sessionId, true))}
                  disabled={submitting}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  {submitting ? "Submitting..." : "Confirm & Submit"}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setStep("choose")} disabled={submitting}>
                  Back
                </Button>
              </div>
            </div>
          ) : step === "substitute-question" ? (
            <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                Was a substitute faculty present instead of{" "}
                <span className="font-bold text-slate-900 dark:text-white">
                  {session.faculty || session.subject}
                </span>?
              </p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={() => setStep("substitute-name")} disabled={submitting}>
                  Yes
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => run(() => submitFacultyAttendance(sessionId, false))}
                  disabled={submitting}
                >
                  No
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setStep("choose")} disabled={submitting}>
                  Back
                </Button>
              </div>
            </div>
          ) : (
            <form
              className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-800 dark:bg-slate-950"
              onSubmit={(e) => {
                e.preventDefault();
                if (!substituteName.trim()) {
                  setNameError("Substitute faculty name is required.");
                  return;
                }
                setNameError(null);
                void run(() => submitSubstitute(sessionId, substituteName.trim()));
              }}
              noValidate
            >
              <div className="space-y-1.5">
                <Label htmlFor="substitute" className="text-xs font-semibold">
                  Substitute Faculty Name
                </Label>
                <Input
                  id="substitute"
                  value={substituteName}
                  onChange={(e) => setSubstituteName(e.target.value)}
                  placeholder="Enter the substitute faculty name"
                  className="bg-white dark:bg-slate-900"
                />
                {nameError ? <p className="text-xs text-rose-500">{nameError}</p> : null}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" type="submit" disabled={submitting}>
                  {submitting ? "Submitting..." : "Submit Substitute"}
                </Button>
                <Button
                  size="sm"
                  type="button"
                  variant="ghost"
                  onClick={() => setStep("substitute-question")}
                  disabled={submitting}
                >
                  Back
                </Button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
