import { useState } from "react";
import { CheckCircle2, Clock, Lock, UserCheck, UserX } from "lucide-react";
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

  const answered = session.facultyResponse !== "Pending";

  const now = new Date();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();
  const startMin = parseMinutes(session.startTime);
  const endMin = parseMinutes(session.endTime);

  const isPastPeriod = currentMinutes > endMin || session.sessionStatus === "Completed";
  const isUpcoming = currentMinutes < startMin && session.sessionStatus === "Upcoming";

  const run = async (action: () => Promise<ClassSession>) => {
    setSubmitting(true);
    try {
      const updated = await action();
      toast.success("Attendance response submitted successfully");
      onSubmitted(updated);
      setStep("choose");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not submit your response.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden dark:border-slate-800 dark:bg-slate-900 transition-all">
      {/* Top Header Bar (Image 1 Header Layout) */}
      <div className="bg-slate-100/90 px-5 py-3.5 border-b border-slate-200 dark:bg-slate-800/80 dark:border-slate-800 flex items-center justify-between">
        <h3 className="text-base font-bold text-slate-900 dark:text-white truncate">
          {session.period} — {session.subject}
        </h3>
        <StatusBadge
          status={
            answered
              ? session.facultyResponse
              : isPastPeriod
              ? "Completed"
              : session.sessionStatus
          }
        />
      </div>

      {/* Card Details Body (Matching Image 1 Key-Value Layout) */}
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

        {/* Card Footer Actions (Matching Image 1 Footer & Strict Lock Rule) */}
        <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
          {answered ? (
            /* Completed & Marked Period -> Read-Only Badge (NO REMARKING!) */
            <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
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
              {session.responseTime ? (
                <span className="text-xs text-slate-400 ml-auto">Responded: {session.responseTime}</span>
              ) : null}
            </div>
          ) : isPastPeriod ? (
            /* Period Ended Without Response -> Locked / Read-Only (NO REMARKING ALLOWED!) */
            <div className="flex items-center gap-3">
              <Button disabled size="sm" variant="outline" className="opacity-50 cursor-not-allowed">
                Period Ended
              </Button>
              <span className="text-xs text-rose-600 dark:text-rose-400 font-medium flex items-center gap-1">
                <Lock className="size-3.5" /> Class period finished — attendance remarking closed
              </span>
            </div>
          ) : isUpcoming ? (
            /* Upcoming Period -> Disabled Button + Opens at <startTime> (Image 1 Style) */
            <div className="flex items-center gap-3">
              <Button disabled size="sm" variant="outline" className="opacity-60 cursor-not-allowed">
                Mark Attendance
              </Button>
              <span className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 font-medium">
                <Clock className="size-3.5 text-slate-400" />
                Opens at {session.startTime}
              </span>
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
                  onClick={() => run(() => submitFacultyAttendance(session.id, true))}
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
                  onClick={() => run(() => submitFacultyAttendance(session.id, false))}
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
                void run(() => submitSubstitute(session.id, substituteName.trim()));
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
