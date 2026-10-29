import { useState, useEffect, useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  CalendarClock,
  CalendarDays,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Edit2,
  Ban,
  RefreshCw,
  Clock,
  User,
  Check,
  Calendar,
} from "lucide-react";
import { MentorLayout } from "@/layouts/MentorLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  createPlannedAbsence,
  getPlannedAbsences,
  updatePlannedAbsence,
  cancelPlannedAbsence,
  type PlannedAbsenceItem,
} from "@/services/plannedAbsenceService";
import {
  getMentorStudents,
  searchMentorStudentsGlobal,
} from "@/services/mentorService";
import type { StudentItem } from "@/services/studentService";

export const Route = createFileRoute("/mentor/planned-absences")({
  component: MentorPlannedAbsencesPage,
});

const REASON_PRESETS = [
  "Medical leave / Health issue",
  "Family function / Emergency",
  "On-Duty (OD) / College Event",
  "Sports competition",
  "External examination / Interview",
  "Personal leave",
];

function MentorPlannedAbsencesPage() {
  const [absences, setAbsences] = useState<PlannedAbsenceItem[]>([]);
  const [assignedStudents, setAssignedStudents] = useState<StudentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [studentsLoading, setStudentsLoading] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [activeOnly, setActiveOnly] = useState(false);

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [rollNumberQuery, setRollNumberQuery] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [creating, setCreating] = useState(false);

  // Selected student auto-lookup memo
  const selectedStudent = useMemo(() => {
    return assignedStudents.find(
      (s) => s.id === selectedStudentId || (s as any)._id === selectedStudentId
    );
  }, [assignedStudents, selectedStudentId]);

  // Dynamically sorted/filtered students for the dropdown
  const displayStudents = useMemo(() => {
    let list = [...assignedStudents];
    if (selectedStudent && !list.some((s) => (s.id || (s as any)._id) === (selectedStudent.id || (selectedStudent as any)._id))) {
      list.unshift(selectedStudent);
    }
    const q = rollNumberQuery.trim().toLowerCase();
    if (!q) return list;
    const qAlt = q.endsWith("el") ? q.slice(0, -2) + "e1" : q.endsWith("e1") ? q.slice(0, -2) + "el" : q;

    return list.sort((a, b) => {
      const aRoll = (a.rollNumber || "").toLowerCase();
      const bRoll = (b.rollNumber || "").toLowerCase();
      const aName = (a.name || "").toLowerCase();
      const bName = (b.name || "").toLowerCase();

      const aExact = aRoll === q || aRoll === qAlt || aName === q;
      const bExact = bRoll === q || bRoll === qAlt || bName === q;
      if (aExact && !bExact) return -1;
      if (!aExact && bExact) return 1;

      const aStarts = aRoll.startsWith(q) || aRoll.startsWith(qAlt) || aName.startsWith(q);
      const bStarts = bRoll.startsWith(q) || bRoll.startsWith(qAlt) || bName.startsWith(q);
      if (aStarts && !bStarts) return -1;
      if (!aStarts && bStarts) return 1;

      const aHas = aRoll.includes(q) || aRoll.includes(qAlt) || aName.includes(q);
      const bHas = bRoll.includes(q) || bRoll.includes(qAlt) || bName.includes(q);
      if (aHas && !bHas) return -1;
      if (!aHas && bHas) return 1;

      return 0;
    });
  }, [assignedStudents, selectedStudent, rollNumberQuery]);

  const handleRollNumberQueryChange = async (val: string) => {
    setRollNumberQuery(val);
    const trimmed = val.trim().toLowerCase();
    if (!trimmed) {
      setSelectedStudentId("");
      return;
    }

    const trimmedAlt = trimmed.endsWith("el")
      ? trimmed.slice(0, -2) + "e1"
      : trimmed.endsWith("e1")
      ? trimmed.slice(0, -2) + "el"
      : trimmed;

    // 1. Immediate local matching (by roll number or name)
    const localMatch =
      assignedStudents.find((s) => {
        const r = (s.rollNumber || "").toLowerCase();
        const n = (s.name || "").toLowerCase();
        return r === trimmed || r === trimmedAlt || n === trimmed;
      }) ||
      assignedStudents.find((s) => {
        const r = (s.rollNumber || "").toLowerCase();
        const n = (s.name || "").toLowerCase();
        return r.startsWith(trimmed) || r.startsWith(trimmedAlt) || n.startsWith(trimmed);
      }) ||
      assignedStudents.find((s) => {
        const r = (s.rollNumber || "").toLowerCase();
        const n = (s.name || "").toLowerCase();
        return r.includes(trimmed) || n.includes(trimmed);
      });

    if (localMatch) {
      setSelectedStudentId(localMatch.id || (localMatch as any)._id);
    }

    // 2. Also query backend search if length >= 2
    if (trimmed.length >= 2) {
      try {
        const results = await searchMentorStudentsGlobal(trimmed);
        if (results && results.length > 0) {
          setAssignedStudents((prev) => {
            const existingIds = new Set(prev.map((s) => s.id || (s as any)._id));
            const toAdd = results.filter((r) => !existingIds.has(r.id || (r as any)._id));
            return [...prev, ...toAdd];
          });

          const best =
            results.find((r) => {
              const roll = (r.rollNumber || "").toLowerCase();
              const name = (r.name || "").toLowerCase();
              return roll === trimmed || roll === trimmedAlt || name === trimmed;
            }) ||
            results.find((r) => {
              const roll = (r.rollNumber || "").toLowerCase();
              const name = (r.name || "").toLowerCase();
              return roll.startsWith(trimmed) || roll.startsWith(trimmedAlt) || name.startsWith(trimmed);
            }) ||
            results[0];

          if (best) {
            setSelectedStudentId(best.id || (best as any)._id);
          }
        }
      } catch (err) {
        console.error("Remote student search error:", err);
      }
    }
  };

  const handleSelectStudentChange = (id: string) => {
    setSelectedStudentId(id);
    const match = assignedStudents.find((s) => (s.id || s._id) === id);
    if (match) {
      setRollNumberQuery(match.rollNumber);
    }
  };

  const applyDatePreset = (daysFromToday: number, durationDays: number) => {
    const start = new Date();
    start.setDate(start.getDate() + daysFromToday);
    const end = new Date(start);
    end.setDate(end.getDate() + (durationDays - 1));
    setStartDate(start.toISOString().slice(0, 10));
    setEndDate(end.toISOString().slice(0, 10));
  };

  // Edit Modal State
  const [editTarget, setEditTarget] = useState<PlannedAbsenceItem | null>(null);
  const [editStartDate, setEditStartDate] = useState("");
  const [editEndDate, setEditEndDate] = useState("");
  const [editReason, setEditReason] = useState("");
  const [updating, setUpdating] = useState(false);

  // Cancel Modal State
  const [cancelTarget, setCancelTarget] = useState<PlannedAbsenceItem | null>(null);
  const [cancellationReason, setCancellationReason] = useState("");
  const [cancelling, setCancelling] = useState(false);

  // Today in local YYYY-MM-DD format
  const todayStr = new Date().toISOString().slice(0, 10);

  const fetchAbsences = async () => {
    try {
      setLoading(true);
      const data = await getPlannedAbsences({
        ...(statusFilter !== "ALL" ? { status: statusFilter } : {}),
        ...(activeOnly ? { activeOnly: true } : {}),
      });
      setAbsences(data);
    } catch (err: any) {
      toast.error(err.message || "Failed to load planned absences.");
    } finally {
      setLoading(false);
    }
  };

  const fetchStudents = async () => {
    try {
      setStudentsLoading(true);
      const data = await getMentorStudents();
      setAssignedStudents(data || []);
    } catch (err: any) {
      console.error("Failed to load students:", err);
      try {
        const fallback = await searchMentorStudentsGlobal("");
        setAssignedStudents(fallback || []);
      } catch (e) {
        console.error("Fallback search failed:", e);
      }
    } finally {
      setStudentsLoading(false);
    }
  };

  useEffect(() => {
    fetchAbsences();
  }, [statusFilter, activeOnly]);

  useEffect(() => {
    fetchStudents();
  }, []);

  const handleOpenCreate = (preselectedStudent?: StudentItem) => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toISOString().slice(0, 10);

    if (preselectedStudent) {
      setSelectedStudentId(preselectedStudent.id || preselectedStudent._id || "");
      setRollNumberQuery(preselectedStudent.rollNumber);
    } else {
      setSelectedStudentId("");
      setRollNumberQuery("");
    }
    setStartDate(tomorrowStr);
    setEndDate(tomorrowStr);
    setReason("");
    setIsCreateOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStudentId) {
      toast.error("Please select a student from your assigned list.");
      return;
    }
    if (!startDate || !endDate) {
      toast.error("Please specify both start and end dates.");
      return;
    }
    if (startDate > endDate) {
      toast.error("Start date cannot be after end date.");
      return;
    }
    if (!reason.trim()) {
      toast.error("Please enter a non-empty reason for the planned absence.");
      return;
    }

    const targetStudent = assignedStudents.find(
      (s) => s.id === selectedStudentId || s._id === selectedStudentId
    );
    if (!targetStudent) return;

    try {
      setCreating(true);
      await createPlannedAbsence({
        studentId: targetStudent.id || targetStudent._id || selectedStudentId,
        rollNumber: targetStudent.rollNumber,
        studentName: targetStudent.name,
        year: targetStudent.year,
        section: targetStudent.section,
        startDate,
        endDate,
        reason: reason.trim(),
      });

      toast.success(`Successfully scheduled leave for ${targetStudent.name} (${startDate} to ${endDate}).`);
      setIsCreateOpen(false);
      await fetchAbsences();
    } catch (err: any) {
      toast.error(err.message || "Failed to record planned absence.");
    } finally {
      setCreating(false);
    }
  };

  const handleOpenEdit = (item: PlannedAbsenceItem) => {
    setEditTarget(item);
    setEditStartDate(item.startDate);
    setEditEndDate(item.endDate);
    setEditReason(item.reason);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editTarget) return;

    if (editStartDate > editEndDate) {
      toast.error("Start date cannot be after end date.");
      return;
    }

    try {
      setUpdating(true);
      await updatePlannedAbsence(editTarget.id, {
        startDate: editStartDate,
        endDate: editEndDate,
        reason: editReason.trim(),
      });

      toast.success("Updated dates and reason successfully.");
      setEditTarget(null);
      await fetchAbsences();
    } catch (err: any) {
      toast.error(err.message || "Failed to update planned absence.");
    } finally {
      setUpdating(false);
    }
  };

  const handleCancelSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cancelTarget) return;

    try {
      setCancelling(true);
      await cancelPlannedAbsence(cancelTarget.id, {
        cancellationReason: cancellationReason.trim() || "Cancelled by mentor",
      });

      toast.success(`Cancelled leave for ${cancelTarget.studentName}.`);
      setCancelTarget(null);
      setCancellationReason("");
      await fetchAbsences();
    } catch (err: any) {
      toast.error(err.message || "Failed to cancel planned absence.");
    } finally {
      setCancelling(false);
    }
  };

  // Filtered absences
  const filteredAbsences = absences.filter((a) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return (
      a.studentName.toLowerCase().includes(q) ||
      a.rollNumber.toLowerCase().includes(q) ||
      a.section.toLowerCase().includes(q) ||
      a.reason.toLowerCase().includes(q)
    );
  });

  const activeTodayCount = absences.filter((a) => a.isActiveToday).length;

  return (
    <MentorLayout>
      <div className="flex flex-col gap-6 p-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <CalendarClock className="size-6 text-primary" />
              Student Planned Absence Management
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Record pre-approved date ranges for student leave. Active planned absences suppress daily calling prompts.
            </p>
          </div>
          <Button
            onClick={() => handleOpenCreate()}
            className="gap-2 shadow-sm bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            <Plus className="size-4" />
            Record Planned Absence
          </Button>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="border-l-4 border-l-primary">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs font-semibold uppercase tracking-wider">
                Active Absences Today
              </CardDescription>
              <CardTitle className="text-2xl font-bold text-primary flex items-center justify-between">
                <span>{activeTodayCount}</span>
                <Clock className="size-5 text-primary/60" />
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Students currently on approved leave today.
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-blue-500">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs font-semibold uppercase tracking-wider">
                Total Planned Records
              </CardDescription>
              <CardTitle className="text-2xl font-bold text-foreground flex items-center justify-between">
                <span>{absences.length}</span>
                <CalendarDays className="size-5 text-blue-500/60" />
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              All planned absences recorded for your assigned students.
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-emerald-500">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs font-semibold uppercase tracking-wider">
                Assigned Students Pool
              </CardDescription>
              <CardTitle className="text-2xl font-bold text-foreground flex items-center justify-between">
                <span>{assignedStudents.length}</span>
                <User className="size-5 text-emerald-500/60" />
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Students eligible for planned leave management.
            </CardContent>
          </Card>
        </div>

        {/* Main List Card */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <Calendar className="size-5 text-primary" />
                  Planned Absence Records ({filteredAbsences.length})
                </CardTitle>
                <CardDescription>
                  View, edit date ranges, or cancel planned absence records.
                </CardDescription>
              </div>

              {/* Filters */}
              <div className="flex flex-wrap items-center gap-2.5">
                <div className="relative w-52">
                  <Search className="size-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search student or roll..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8 h-9 text-xs"
                  />
                </div>

                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-36 h-9 text-xs">
                    <SelectValue placeholder="All Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Status</SelectItem>
                    <SelectItem value="ACTIVE">Active</SelectItem>
                    <SelectItem value="CANCELLED">Cancelled</SelectItem>
                  </SelectContent>
                </Select>

                <Button
                  variant={activeOnly ? "default" : "outline"}
                  size="sm"
                  onClick={() => setActiveOnly(!activeOnly)}
                  className="h-9 text-xs gap-1.5"
                >
                  <Clock className="size-3.5" />
                  Active Today Only
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchAbsences}
                  disabled={loading}
                  className="h-9 px-2.5"
                >
                  <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {loading ? (
              <div className="py-12 text-center text-muted-foreground flex flex-col items-center gap-2">
                <RefreshCw className="size-6 animate-spin text-primary" />
                <p className="text-sm">Loading planned absences...</p>
              </div>
            ) : filteredAbsences.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground border rounded-lg border-dashed flex flex-col items-center gap-2">
                <CalendarClock className="size-8 text-muted-foreground/50" />
                <p className="text-sm font-medium">No planned absences recorded.</p>
                <p className="text-xs text-muted-foreground max-w-sm">
                  Click "Record Planned Absence" above to schedule a leave period for an assigned student.
                </p>
              </div>
            ) : (
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Student Name</TableHead>
                      <TableHead>Roll Number</TableHead>
                      <TableHead>Class</TableHead>
                      <TableHead>Absence Period</TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredAbsences.map((item) => (
                      <TableRow key={item.id} className={item.status === "CANCELLED" ? "opacity-60 bg-muted/20" : ""}>
                        <TableCell className="font-semibold text-foreground">
                          {item.studentName}
                        </TableCell>
                        <TableCell className="font-mono text-xs font-medium">
                          {item.rollNumber}
                        </TableCell>
                        <TableCell>
                          <span className="text-xs text-muted-foreground">
                            {item.year} - <Badge variant="outline" className="text-xs">{item.section}</Badge>
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col text-xs">
                            <span className="font-semibold text-foreground">
                              {item.startDate} to {item.endDate}
                            </span>
                            {item.isActiveToday && (
                              <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400 mt-0.5">
                                • In Effect Today
                              </span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-xs">
                          <p className="text-xs text-foreground truncate" title={item.reason}>
                            {item.reason}
                          </p>
                          {item.cancellationReason && (
                            <p className="text-[11px] text-destructive truncate mt-0.5" title={item.cancellationReason}>
                              Cancelled: {item.cancellationReason}
                            </p>
                          )}
                        </TableCell>
                        <TableCell>
                          {item.status === "CANCELLED" ? (
                            <Badge variant="outline" className="border-destructive/40 text-destructive text-xs">
                              Cancelled
                            </Badge>
                          ) : item.isActiveToday ? (
                            <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs gap-1">
                              <CheckCircle2 className="size-3" />
                              Active Today
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-xs">
                              Scheduled
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {item.status === "ACTIVE" ? (
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenEdit(item)}
                                className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                                title="Edit date range or reason"
                              >
                                <Edit2 className="size-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setCancelTarget(item)}
                                className="h-8 w-8 p-0 text-destructive hover:bg-destructive/10"
                                title="Cancel planned absence"
                              >
                                <Ban className="size-4" />
                              </Button>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground italic">No actions</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Record Planned Absence Modal */}
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CalendarClock className="size-5 text-primary" />
                Record Student Planned Absence
              </DialogTitle>
              <DialogDescription>
                Schedule an approved absence period for an assigned student.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleCreateSubmit} className="space-y-4 py-2">
              {/* Student Details Lookup & Dropdown */}
              <div className="space-y-2.5">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground">
                    Search Student Details (Roll Number or Name) <span className="text-destructive">*</span>
                  </label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      placeholder="Type roll number or student name (e.g. 23471A05EL, 24471A0575, Pallavi)..."
                      value={rollNumberQuery}
                      onChange={(e) => handleRollNumberQueryChange(e.target.value)}
                      className="pl-9 pr-8 text-xs"
                    />
                    {rollNumberQuery && (
                      <button
                        type="button"
                        onClick={() => handleRollNumberQueryChange("")}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-xs font-bold p-1"
                        title="Clear search"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                </div>

                {/* Dropdown displaying particular student name by default */}
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground flex items-center justify-between">
                    <span>Assigned Student Dropdown:</span>
                    {studentsLoading && <span className="text-primary text-[10px] animate-pulse">Searching roster...</span>}
                  </label>
                  <Select value={selectedStudentId} onValueChange={handleSelectStudentChange}>
                    <SelectTrigger className="w-full text-xs h-9">
                      <SelectValue placeholder={studentsLoading ? "Loading assigned students..." : "Choose assigned student..."}>
                        {selectedStudent ? (
                          <span className="font-semibold text-foreground">
                            {selectedStudent.name}{" "}
                            <span className="text-muted-foreground font-mono font-normal">
                              ({selectedStudent.rollNumber} &bull; {selectedStudent.year}, Sec {selectedStudent.section})
                            </span>
                          </span>
                        ) : undefined}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent className="max-h-60">
                      {displayStudents.map((s) => {
                        const sid = s.id || (s as any)._id;
                        return (
                          <SelectItem key={sid} value={sid} className="text-xs">
                            <span className="font-semibold text-foreground">{s.name}</span>{" "}
                            <span className="text-muted-foreground font-mono text-[11px]">
                              ({s.rollNumber} &bull; {s.year}, Sec {s.section})
                            </span>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                </div>

                {/* Verified Student Details Card */}
                {selectedStudent ? (
                  <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-2.5 text-xs flex items-center justify-between animate-in fade-in-50">
                    <div>
                      <div className="font-semibold text-foreground flex items-center gap-1.5">
                        <User className="size-3.5 text-emerald-600 shrink-0" />
                        <span className="font-bold text-foreground">{selectedStudent.name}</span>
                        <Badge variant="outline" className="text-[10px] bg-background font-mono font-bold">
                          {selectedStudent.rollNumber}
                        </Badge>
                      </div>
                      <div className="text-muted-foreground text-[11px] mt-0.5">
                        Academic Year: <strong className="text-foreground">{selectedStudent.year}</strong> &bull; Section: <strong className="text-foreground">{selectedStudent.section}</strong>
                      </div>
                    </div>
                    <Badge className="bg-emerald-600 text-white text-[10px]">
                      Student Verified
                    </Badge>
                  </div>
                ) : rollNumberQuery.trim() && !studentsLoading ? (
                  <p className="text-[11px] text-amber-600 dark:text-amber-400">
                    No matching student found for "{rollNumberQuery}". You can choose directly from the dropdown above.
                  </p>
                ) : null}
              </div>

              {/* Quick Date Presets & Date Range */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-foreground">
                    Advance Leave Dates <span className="text-destructive">*</span>
                  </label>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => applyDatePreset(1, 1)}
                      className="text-[10px] px-2 py-0.5 rounded border bg-muted/60 hover:bg-primary/10 hover:border-primary/40 text-foreground transition-colors"
                      title="Starts tomorrow for 1 day"
                    >
                      Tomorrow (1 day)
                    </button>
                    <button
                      type="button"
                      onClick={() => applyDatePreset(1, 3)}
                      className="text-[10px] px-2 py-0.5 rounded border bg-muted/60 hover:bg-primary/10 hover:border-primary/40 text-foreground transition-colors"
                      title="Starts tomorrow for 3 days"
                    >
                      Next 3 Days
                    </button>
                    <button
                      type="button"
                      onClick={() => applyDatePreset(1, 7)}
                      className="text-[10px] px-2 py-0.5 rounded border bg-muted/60 hover:bg-primary/10 hover:border-primary/40 text-foreground transition-colors"
                      title="Starts tomorrow for 7 days"
                    >
                      Next Week (7 days)
                    </button>
                    <button
                      type="button"
                      onClick={() => applyDatePreset(0, 1)}
                      className="text-[10px] px-2 py-0.5 rounded border bg-muted/60 hover:bg-primary/10 hover:border-primary/40 text-foreground transition-colors"
                      title="Today only"
                    >
                      Today
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-medium text-muted-foreground">From Date</label>
                    <Input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      required
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[11px] font-medium text-muted-foreground">To Date</label>
                    <Input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      required
                      className="text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* Preset Reason Chips */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  Quick Reason Presets:
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {REASON_PRESETS.map((preset) => (
                    <button
                      type="button"
                      key={preset}
                      onClick={() => setReason(preset)}
                      className="text-[11px] px-2.5 py-1 rounded-full border bg-muted/40 hover:bg-primary/10 hover:border-primary/40 transition-colors text-foreground"
                    >
                      {preset}
                    </button>
                  ))}
                </div>
              </div>

              {/* Mandatory Reason */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Absence Reason <span className="text-destructive">*</span>
                </label>
                <Textarea
                  placeholder="Enter medical reason, approved leave detail, or remarks..."
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  rows={3}
                  required
                />
              </div>

              <DialogFooter className="mt-4 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCreateOpen(false)}
                  disabled={creating}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={creating} className="gap-2">
                  {creating ? <RefreshCw className="size-4 animate-spin" /> : <Check className="size-4" />}
                  Save Planned Absence
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Edit Modal */}
        <Dialog open={!!editTarget} onOpenChange={(open) => !open && setEditTarget(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Edit2 className="size-5 text-primary" />
                Edit Planned Absence
              </DialogTitle>
              <DialogDescription>
                Update leave period or reason for <span className="font-semibold text-foreground">{editTarget?.studentName}</span>.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleEditSubmit} className="space-y-4 py-2">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Start Date</label>
                  <Input
                    type="date"
                    value={editStartDate}
                    onChange={(e) => setEditStartDate(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">End Date</label>
                  <Input
                    type="date"
                    value={editEndDate}
                    onChange={(e) => setEditEndDate(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Reason</label>
                <Textarea
                  value={editReason}
                  onChange={(e) => setEditReason(e.target.value)}
                  rows={3}
                  required
                />
              </div>

              <DialogFooter className="gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setEditTarget(null)}
                  disabled={updating}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={updating} className="gap-2">
                  {updating ? <RefreshCw className="size-4 animate-spin" /> : <Check className="size-4" />}
                  Update Absence
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Cancel Modal */}
        <Dialog open={!!cancelTarget} onOpenChange={(open) => !open && setCancelTarget(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-destructive">
                <Ban className="size-5" />
                Cancel Planned Absence
              </DialogTitle>
              <DialogDescription>
                Are you sure you want to cancel the planned leave for{" "}
                <span className="font-semibold text-foreground">{cancelTarget?.studentName}</span> ({cancelTarget?.startDate} to {cancelTarget?.endDate})?
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleCancelSubmit} className="space-y-4 py-2">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Cancellation Note / Reason
                </label>
                <Input
                  placeholder="e.g. Student returned early, event cancelled..."
                  value={cancellationReason}
                  onChange={(e) => setCancellationReason(e.target.value)}
                  required
                />
              </div>

              <DialogFooter className="gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setCancelTarget(null)}
                  disabled={cancelling}
                >
                  Back
                </Button>
                <Button
                  type="submit"
                  variant="destructive"
                  disabled={cancelling}
                  className="gap-2"
                >
                  {cancelling ? <RefreshCw className="size-4 animate-spin" /> : <Ban className="size-4" />}
                  Confirm Cancellation
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </MentorLayout>
  );
}
