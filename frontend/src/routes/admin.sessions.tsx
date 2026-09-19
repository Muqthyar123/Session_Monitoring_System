import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AdminLayout } from "@/layouts/AdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getSessions } from "@/services/sessionService";
import { MOCK_SECTIONS, type ClassSession } from "@/data/mock/mockData";

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

const ALL = "all";

const columns: Column<ClassSession>[] = [
  { key: "section", header: "Section", cell: (r) => r.section },
  { key: "subject", header: "Subject", cell: (r) => r.subject },
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
    cell: (r) => (
      <div className="flex flex-wrap items-center gap-1">
        <StatusBadge status={r.facultyResponse} />
        {r.responseWindowExpired && r.facultyResponse === "Pending" ? (
          <StatusBadge status="Expired" />
        ) : null}
      </div>
    ),
  },
  { key: "responseTime", header: "Response Time", cell: (r) => r.responseTime ?? "—" },
  { key: "substitute", header: "Substitute", cell: (r) => r.substituteName ?? "—" },
];

function SessionsPage() {
  const { data, loading, error, reload } = useAsyncData(() => getSessions(), []);
  const [sectionFilter, setSectionFilter] = useState(ALL);
  const [statusFilter, setStatusFilter] = useState(ALL);

  const availableSections = useMemo(() => {
    const defaultSecs = [
      "II-CSE-A", "II-CSE-B", "II-CSE-C", "II-CSE-D", "II-CSE-E",
      "II-CSE-F", "II-CSE-G", "II-CSE-H", "II-CSE-I", "II-CSE-J"
    ];
    const fromData = (data ?? []).map((s) => s.section).filter(Boolean);
    return Array.from(new Set([...defaultSecs, ...fromData])).sort();
  }, [data]);

  const rows = useMemo(
    () =>
      (data ?? []).filter(
        (s) =>
          (sectionFilter === ALL || s.section === sectionFilter) &&
          (statusFilter === ALL || s.sessionStatus === statusFilter),
      ),
    [data, sectionFilter, statusFilter],
  );

  return (
    <AdminLayout>
      <PageHeader
        title="Sessions / Monitoring"
        description="Actual class occurrences that require a CR/LR response. Continuous periods are shown as one combined session."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:w-2/3">
        <Select value={sectionFilter} onValueChange={setSectionFilter}>
          <SelectTrigger aria-label="Filter by section">
            <SelectValue placeholder="Section" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All sections</SelectItem>
            {availableSections.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger aria-label="Filter by session status">
            <SelectValue placeholder="Session status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            <SelectItem value="Upcoming">Upcoming</SelectItem>
            <SelectItem value="Active">Active</SelectItem>
            <SelectItem value="Completed">Completed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <LoadingState rows={5} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : rows.length === 0 ? (
        <EmptyState title="No sessions" description="No sessions match the current filters." />
      ) : (
        <DataTable columns={columns} rows={rows} getRowId={(r) => r.id} />
      )}
    </AdminLayout>
  );
}
