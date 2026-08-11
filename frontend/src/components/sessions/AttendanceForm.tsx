import { useState } from "react";
import { CheckCircle2, UserX } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ResponseWindow } from "@/components/sessions/ResponseWindow";
import { submitFacultyAttendance, submitSubstitute } from "@/services/sessionService";
import type { ClassSession } from "@/data/mock/mockData";

type Step = "choose" | "confirm-present" | "substitute-question" | "substitute-name";

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

  const run = async (action: () => Promise<ClassSession>) => {
    setSubmitting(true);
    try {
      const updated = await action();
      toast.success("Response submitted");
      onSubmitted(updated);
      setStep("choose");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not submit your response.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader className="space-y-2">
        <CardTitle className="text-base">Current Session</CardTitle>
        <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Section</dt>
          <dd className="truncate">{session.section}</dd>
          <dt className="text-muted-foreground">Subject</dt>
          <dd className="truncate">{session.subject}</dd>
          <dt className="text-muted-foreground">Time</dt>
          <dd>
            {session.startTime} - {session.endTime}
          </dd>
          <dt className="text-muted-foreground">Status</dt>
          <dd>
            <StatusBadge status={session.sessionStatus} />
          </dd>
        </dl>
        <ResponseWindow session={session} />
      </CardHeader>

      <CardContent className="space-y-4">
        <h3 className="text-sm font-semibold">Faculty Attendance</h3>

        {answered ? (
          <div className="rounded-md border border-border p-3 text-sm">
            <p className="flex items-center gap-2 font-medium">
              <CheckCircle2 className="size-4 text-success" /> Response recorded
            </p>
            <p className="mt-1 text-muted-foreground">
              {session.facultyResponse}
              {session.substituteName ? ` — ${session.substituteName}` : ""}
              {session.responseTime ? ` at ${session.responseTime}` : ""}
            </p>
          </div>
        ) : step === "choose" ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <Button size="lg" onClick={() => setStep("confirm-present")} disabled={submitting}>
              <CheckCircle2 className="size-4" /> Faculty Present
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => setStep("substitute-question")}
              disabled={submitting}
            >
              <UserX className="size-4" /> Faculty Not Present
            </Button>
          </div>
        ) : step === "confirm-present" ? (
          <div className="space-y-3 rounded-md border border-border p-3">
            <p className="text-sm">Confirm that the assigned faculty is present for this session?</p>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => run(() => submitFacultyAttendance(session.id, true))}
                disabled={submitting}
              >
                {submitting ? "Submitting..." : "Confirm & Submit"}
              </Button>
              <Button variant="ghost" onClick={() => setStep("choose")} disabled={submitting}>
                Back
              </Button>
            </div>
          </div>
        ) : step === "substitute-question" ? (
          <div className="space-y-3 rounded-md border border-border p-3">
            <p className="text-sm font-medium">Was a substitute faculty present?</p>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => setStep("substitute-name")} disabled={submitting}>
                Yes
              </Button>
              <Button
                variant="outline"
                onClick={() => run(() => submitFacultyAttendance(session.id, false))}
                disabled={submitting}
              >
                No
              </Button>
              <Button variant="ghost" onClick={() => setStep("choose")} disabled={submitting}>
                Back
              </Button>
            </div>
          </div>
        ) : (
          <form
            className="space-y-3 rounded-md border border-border p-3"
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
              <Label htmlFor="substitute">Substitute Faculty Name</Label>
              <Input
                id="substitute"
                value={substituteName}
                onChange={(e) => setSubstituteName(e.target.value)}
                placeholder="Enter the substitute faculty name"
              />
              {nameError ? <p className="text-xs text-destructive">{nameError}</p> : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={submitting}>
                {submitting ? "Submitting..." : "Submit"}
              </Button>
              <Button
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
      </CardContent>
    </Card>
  );
}
