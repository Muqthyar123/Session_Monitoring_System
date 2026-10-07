import { useEffect, useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Download, RefreshCw, Filter, Calendar, Layers, Clock } from "lucide-react";
import { exportToExcel } from "@/utils/exportUtils";
import { AdminLayout } from "@/layouts/AdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { getSessions } from "@/services/sessionService";
import { getSections, type Section } from "@/services/sectionService";
import type { ClassSession } from "@/data/mock/mockData";
import { toast } from "sonner";

export const Route = createFileRoute("/admin/sessions")({
  head: () => ({
    meta: [
      { title: "Session Monitoring — Faculty Attendance Monitor" },
      { name: "description", content: "Monitor active and recent class sessions, CR/LR responses and substitute faculty reports." },
      { property: "og:title", content: "Session Monitoring — Faculty Attendance Monitor" },
      { property: "og:description", content: "Track class sessions and CR/LR faculty attendance responses." },
    ],
  }),
  component: SessionsPage,
});

const ALL = "ALL";
const ACADEMIC_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"];

const columns: Column<ClassSession>[] = [
  {
    key: "section",
    header: "Section",
    cell: (r) => (
      <div className="font-semibold text-primary">{r.section}</div>
    ),
  },
  { key: "subject", header: "Subject", cell: (r) => <span className="font-medium">{r.subject}</span> },
  { key: "faculty", header: "Assigned Faculty", cell: (r) => r.faculty || "—" },
  { key: "period", header: "Period", cell: (r) => r.period },
  { key: "start", header: "Start", cell: (r) => r.startTime },
  { key: "end", header: "End", cell: (r) => r.endTime },
  { key: "crlr", header: "CR/LR", cell: (r) => `${r.crlrName} (${r.crlrRole})` },
  {
    key: "sessionStatus",
    header: "Session",
    cell: (r) => <StatusBadge status={r.sessionStatus} />,
  },
  {
    key: "response",
    header: "Faculty Response",
    cell: (r) => {
      const resp = r.facultyResponse || "Pending";
      return (
        <div className="flex flex-wrap items-center gap-1">
          <StatusBadge status={resp} />
          {r.responseWindowExpired && resp === "Pending" ? (
            <StatusBadge status="Expired" />
          ) : null}
        </div>
      );
    },
  },
  { key: "responseTime", header: "Response Time", cell: (r) => r.responseTime ?? "—" },
  {
    key: "substitute",
    header: "Substitute",
    cell: (r) =>
      r.substituteName ? (
        <span className="text-blue-600 font-medium">{r.substituteName}</span>
      ) : (
        "—"
      ),
  },
];

function SessionsPage() {
  const [sessions, setSessions] = useState<ClassSession[]>([]);
  const [dbSections, setDbSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [yearFilter, setYearFilter] = useState<string>(ALL);
  const [sectionFilter, setSectionFilter] = useState<string>(ALL);
  const [statusFilter, setStatusFilter] = useState<string>(ALL);
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [sessionsData, sectionsData] = await Promise.all([
        getSessions({
          year: yearFilter === ALL ? undefined : yearFilter,
          section: sectionFilter === ALL ? undefined : sectionFilter,
          status: statusFilter === ALL ? undefined : statusFilter,
          date: selectedDate,
        }),
        getSections().catch(() => []),
      ]);
      setSessions(sessionsData);
      setDbSections(sectionsData);
    } catch (err: any) {
      setError(err.message || "Failed to load class sessions.");
      toast.error(err.message || "Failed to load class sessions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [yearFilter, sectionFilter, statusFilter, selectedDate]);

  // Dynamically compute section options based on the selected year
  const availableSections = useMemo(() => {
    let list = dbSections;
    if (yearFilter !== ALL) {
      list = list.filter((s) => {
        const y = s.year || "";
        return y.toLowerCase().includes(yearFilter.replace("Year", "").trim().toLowerCase());
      });
    }

    const secNames = list.map((s) => s.sectionName || s.department || "").filter(Boolean);
    const fromSessions = sessions.map((s) => s.section).filter(Boolean);
    return Array.from(new Set([...secNames, ...fromSessions])).sort();
  }, [dbSections, yearFilter, sessions]);

  // Client-side fallback filter to guarantee exact results even on cached responses
  const rows = useMemo(() => {
    return sessions.filter((s) => {
      if (yearFilter !== ALL) {
        const yr = (s as any).year || "";
        if (yr && !yr.toLowerCase().includes(yearFilter.replace("Year", "").trim().toLowerCase())) {
          return false;
        }
      }
      if (sectionFilter !== ALL && s.section !== sectionFilter) {
        return false;
      }
      if (statusFilter !== ALL) {
        const sf = statusFilter.toUpperCase();
        const currStatus = (s.sessionStatus || "").toUpperCase();
        const currResp = (s.facultyResponse || "").toUpperCase();

        if (sf === "COMPLETED") {
          const isCompleted =
            currStatus === "COMPLETED" ||
            ["PRESENT", "ABSENT", "NOT PRESENT", "SUBSTITUTE"].includes(currResp);
          if (!isCompleted) return false;
        } else if (sf === "ACTIVE" || sf === "LIVE") {
          if (currStatus !== "ACTIVE") return false;
        } else if (sf === "UPCOMING") {
          if (currStatus !== "UPCOMING") return false;
        } else if (sf === "EXPIRED") {
          if (currStatus !== "EXPIRED") return false;
        }
      }
      return true;
    });
  }, [sessions, yearFilter, sectionFilter, statusFilter]);

  const handleExport = () => {
    const exportData = rows.map((r) => ({
      Section: r.section,
      Subject: r.subject,
      "Assigned Faculty": r.faculty || "—",
      Period: r.period,
      "Start Time": r.startTime,
      "End Time": r.endTime,
      "CR/LR": `${r.crlrName} (${r.crlrRole})`,
      "Session Status": r.sessionStatus,
      "Faculty Response": r.facultyResponse || "Pending",
      "Response Time": r.responseTime || "—",
      "Substitute Faculty": r.substituteName || "—",
      Date: selectedDate,
    }));
    exportToExcel(exportData, `Session_Monitoring_${selectedDate}`);
    toast.success("Sessions monitoring logs exported successfully.");
  };

  return (
    <AdminLayout>
      <PageHeader
        title="Sessions / Monitoring"
        description="Monitor live and completed class sessions, faculty attendance statuses, and CR/LR response submissions."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
              <RefreshCw className={`size-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={rows.length === 0}
              className="bg-emerald-600/10 text-emerald-600 hover:bg-emerald-600/20 border-emerald-500/30"
            >
              <Download className="size-4 mr-2" />
              Export
            </Button>
          </div>
        }
      />

      {/* Filter Toolbar */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 bg-card p-4 rounded-xl border shadow-sm">
        {/* Date Picker */}
        <div>
          <Label className="text-xs text-muted-foreground mb-1 block">Date</Label>
          <Input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
          />
        </div>

        {/* Year Filter */}
        <div>
          <Label className="text-xs text-muted-foreground mb-1 block">Academic Year</Label>
          <Select
            value={yearFilter}
            onValueChange={(val) => {
              setYearFilter(val);
              setSectionFilter(ALL); // reset section filter on year change
            }}
          >
            <SelectTrigger aria-label="Filter by year">
              <SelectValue placeholder="All Years" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All Years</SelectItem>
              {ACADEMIC_YEARS.map((y) => (
                <SelectItem key={y} value={y}>
                  {y}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Section Filter */}
        <div>
          <Label className="text-xs text-muted-foreground mb-1 block">Section</Label>
          <Select value={sectionFilter} onValueChange={setSectionFilter}>
            <SelectTrigger aria-label="Filter by section">
              <SelectValue placeholder="All Sections" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All Sections</SelectItem>
              {availableSections.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Status Filter */}
        <div>
          <Label className="text-xs text-muted-foreground mb-1 block">Session Status</Label>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger aria-label="Filter by session status">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All Statuses</SelectItem>
              <SelectItem value="Active">Active / Live</SelectItem>
              <SelectItem value="Upcoming">Upcoming</SelectItem>
              <SelectItem value="Completed">Completed</SelectItem>
              <SelectItem value="Expired">Expired</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading ? (
        <LoadingState rows={5} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No sessions found"
          description={`No sessions match the selected filters for ${selectedDate}.`}
        />
      ) : (
        <DataTable columns={columns} rows={rows} getRowId={(r) => r.id} />
      )}
    </AdminLayout>
  );
}
