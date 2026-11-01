import { useState } from "react";
import { Phone, PhoneCall, History } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { getAbsenteeCallHistory, initiateAbsenteeCall, updateAbsenteeCallOutcome, type AbsenteeCallRecord } from "@/services/studentAttendanceService";

const OUTCOMES = ["CONNECTED", "NOT_ANSWERED", "BUSY", "SWITCHED_OFF", "WRONG_NUMBER", "CALL_BACK_LATER", "OTHER"];
const label = (value?: string | null) => value ? value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (x) => x.toUpperCase()) : "Pending Outcome";

export function CallHistoryPanel({ attendanceId, studentPhone, parentPhone }: { attendanceId: string; studentPhone?: string | undefined; parentPhone?: string | undefined }) {
  const [calls, setCalls] = useState<AbsenteeCallRecord[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [startingCall, setStartingCall] = useState(false);
  const startCall = async (phone: string, contactType: "PARENT" | "STUDENT") => {
    if (startingCall) return;
    setStartingCall(true);
    try {
      await initiateAbsenteeCall({ attendanceId, phoneNumber: phone, contactType, clientCallId: crypto.randomUUID() });
      toast.success("Call initiation recorded. Outcome remains pending until you record it.");
      setCalls(await getAbsenteeCallHistory(attendanceId));
    } catch (err: any) { toast.error(err.message || "Could not record call initiation."); }
    finally { setStartingCall(false); }
  };
  const showHistory = async () => {
    setExpanded((prev) => !prev);
    if (!expanded) { setLoading(true); try { setCalls(await getAbsenteeCallHistory(attendanceId)); } catch (err: any) { toast.error(err.message || "Could not load call history."); } finally { setLoading(false); } }
  };
  const recordOutcome = async (call: AbsenteeCallRecord) => {
    const choice = window.prompt(`Enter call outcome: ${OUTCOMES.join(", ")}`, call.outcome || "CONNECTED");
    if (!choice) return;
    const outcome = choice.trim().toUpperCase().replaceAll(" ", "_");
    if (!OUTCOMES.includes(outcome)) { toast.error("Choose one of the listed outcomes."); return; }
    const followUpNotes = window.prompt("Follow-up notes (optional):", call.follow_up_notes || "") || "";
    try { await updateAbsenteeCallOutcome(call.id, { outcome, followUpNotes }); setCalls(await getAbsenteeCallHistory(attendanceId)); toast.success("Call outcome saved."); }
    catch (err: any) { toast.error(err.message || "Could not save call outcome."); }
  };
  return <div className="space-y-2">
    <div className="grid grid-cols-2 gap-2">
      {studentPhone ? <a href={`tel:${studentPhone}`} onClick={() => void startCall(studentPhone, "STUDENT")} aria-disabled={startingCall} className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-xs font-semibold text-white"><Phone className="size-3.5" />Call Student</a> : <Button variant="outline" size="sm" disabled>No Student Phone</Button>}
      {parentPhone ? <a href={`tel:${parentPhone}`} onClick={() => void startCall(parentPhone, "PARENT")} aria-disabled={startingCall} className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white"><PhoneCall className="size-3.5" />Call Parent</a> : <Button variant="outline" size="sm" disabled>No Parent Phone</Button>}
    </div>
    <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => void showHistory()}><History className="mr-1 size-3.5" />{expanded ? "Hide" : "View"} call history</Button>
    {expanded && (loading ? <p className="text-xs text-muted-foreground">Loading call history…</p> : calls.length ? <div className="space-y-2 rounded-md border p-2">{calls.map((call) => <div key={call.id} className="rounded border p-2 text-xs"><div className="font-medium">{label(call.contact_type)} · {call.phone_number}</div><div>{call.staff_name} · Initiated {new Date(call.initiated_at).toLocaleString()}</div><div>Outcome: {label(call.outcome)}{call.follow_up_notes ? ` · ${call.follow_up_notes}` : ""}</div>{call.outcome_updated_at && <div>Outcome updated by {call.outcome_updated_by || "Staff"} · {new Date(call.outcome_updated_at).toLocaleString()}</div>}{!call.outcome && <Button variant="outline" size="sm" className="mt-1 h-7" onClick={() => void recordOutcome(call)}>Record outcome</Button>}</div>)}</div> : <p className="text-xs text-muted-foreground">No calls recorded for this absence.</p>)}
  </div>;
}
