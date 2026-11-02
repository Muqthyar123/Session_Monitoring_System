import { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { BellRing, Download, CheckCheck, RefreshCw, Filter, AlertTriangle, Clock, UserX, Info, ChevronDown } from "lucide-react";
import { downloadApiFile } from "@/services/apiClient";
import { AdminLayout } from "@/layouts/AdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { getAdminAlertHistory, acknowledgeAlert } from "@/services/sessionService";
import type { AdminAlert } from "@/data/mock/mockData";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

export const Route = createFileRoute("/admin/alerts")({
  head: () => ({
    meta: [
      { title: "Alerts — Faculty Attendance Monitor" },
      { name: "description", content: "Faculty attendance alerts raised when faculty is unavailable or no CR/LR response is received." },
      { property: "og:title", content: "Alerts — Faculty Attendance Monitor" },
      { property: "og:description", content: "Faculty attendance alerts for unavailable faculty and missed responses." },
    ],
  }),
  component: AlertsPage,
});

const ALL = "ALL";

function AlertsPage() {
  const [alerts, setAlerts] = useState<AdminAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>(ALL);
  const [statusFilter, setStatusFilter] = useState<string>(ALL);
  const [dateFilter, setDateFilter] = useState("ALL");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [appliedRange, setAppliedRange] = useState<{ fromDate?: string; toDate?: string }>({});
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
      const yesterday = new Date(new Date(`${today}T12:00:00+05:30`).getTime() - 86400000).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
      const range = dateFilter === "TODAY" ? { fromDate: today, toDate: today } : dateFilter === "YESTERDAY" ? { fromDate: yesterday, toDate: yesterday } : dateFilter === "CUSTOM" ? appliedRange : {};
      const data = await getAdminAlertHistory({ ...range, category: categoryFilter, status: statusFilter, page, limit: 50, search });
      setAlerts(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || "Failed to load notifications and alerts.");
      toast.error(err.message || "Failed to load notifications and alerts.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [categoryFilter, statusFilter, dateFilter, appliedRange, page, search]);

  const handleAcknowledge = async (alertId: string) => {
    try {
      await acknowledgeAlert(alertId);
      toast.success("Alert acknowledged.");
      await loadData();
    } catch (err: any) {
      toast.error(err.message || "Failed to acknowledge alert.");
    }
  };

  const filteredAlerts = alerts;

  const handleExport = async (format: "pdf" | "xlsx" | "csv") => {
    try {
      const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
      const yesterday = new Date(new Date(`${today}T12:00:00+05:30`).getTime() - 86400000).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
      const range = dateFilter === "TODAY" ? { fromDate: today, toDate: today } : dateFilter === "YESTERDAY" ? { fromDate: yesterday, toDate: yesterday } : dateFilter === "CUSTOM" ? appliedRange : {};
      const params = new URLSearchParams({ format });
      if (range.fromDate) params.set("fromDate", range.fromDate);
      if (range.toDate) params.set("toDate", range.toDate);
      await downloadApiFile(`/attendance/alerts/export?${params}`, `Notification_History.${format}`);
    } catch (err: any) { toast.error(err.message || "Could not export notification history."); }
  };

  return (
    <AdminLayout>
      <PageHeader
        title="Notifications / Alerts"
        description="Monitor high-priority system alerts including student 10-minute response timeouts, faculty absences, and status updates."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
              <RefreshCw className={`size-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm"><Download className="size-4" />Export<ChevronDown className="size-4" /></Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="min-w-40">
                {(["pdf", "xlsx", "csv"] as const).map((format) => (
                  <DropdownMenuItem key={format} onSelect={() => void handleExport(format)}>
                    <Download className="size-4" />{format.toUpperCase()}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        }
      />

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center gap-3 bg-card p-4 rounded-xl border shadow-sm">
        <div className="w-52"><Label className="text-xs text-muted-foreground mb-1 block">Date range</Label><Select value={dateFilter} onValueChange={(value) => { setDateFilter(value); setPage(1); }}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ALL">All history</SelectItem><SelectItem value="TODAY">Today</SelectItem><SelectItem value="YESTERDAY">Yesterday</SelectItem><SelectItem value="CUSTOM">Custom Date Range</SelectItem></SelectContent></Select></div>
        {dateFilter === "CUSTOM" && <><div><Label className="text-xs text-muted-foreground mb-1 block">From date</Label><Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} /></div><div><Label className="text-xs text-muted-foreground mb-1 block">To date</Label><Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} /></div><Button className="mt-5" variant="outline" onClick={() => { if (fromDate && toDate && fromDate > toDate) { toast.error("From date cannot be later than To date."); return; } setAppliedRange({ ...(fromDate ? { fromDate } : {}), ...(toDate ? { toDate } : {}) }); setPage(1); }}>Apply Filter</Button><Button className="mt-5" variant="ghost" onClick={() => { setFromDate(""); setToDate(""); setAppliedRange({}); setPage(1); }}>Clear</Button></>}
        <div className="w-64"><Label className="text-xs text-muted-foreground mb-1 block">Search history</Label><Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Message, section, subject…" /></div>
        <div className="w-64">
          <Label className="text-xs text-muted-foreground mb-1 block">Alert Category</Label>
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger>
              <SelectValue placeholder="All Categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All Alerts</SelectItem>
              <SelectItem value="NO_RESPONSE_10MIN">Student Not Responded (10-Min Timeout)</SelectItem>
              <SelectItem value="FACULTY_ABSENT">Faculty Not Present / Substitute</SelectItem>
              <SelectItem value="FACULTY_STATUS_UPDATED">Faculty Status Updated</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="w-48">
          <Label className="text-xs text-muted-foreground mb-1 block">Status</Label>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger>
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All Statuses</SelectItem>
              <SelectItem value="New">New / Unacknowledged</SelectItem>
              <SelectItem value="Acknowledged">Acknowledged</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {(categoryFilter !== ALL || statusFilter !== ALL) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setCategoryFilter(ALL);
              setStatusFilter(ALL);
            }}
            className="mt-5 text-xs text-muted-foreground hover:text-foreground"
          >
            Reset Filters
          </Button>
        )}
      </div>

      {loading ? (
        <LoadingState rows={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : filteredAlerts.length === 0 ? (
        <EmptyState
          title="No alerts found"
          description="There are no alerts matching the selected filters right now."
          icon={BellRing}
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {filteredAlerts.map((alert) => {
            const isTimeout = (alert.reason || "").toLowerCase().includes("10 min");
            const isAbsent = (alert.reason || "").toLowerCase().includes("not available") || (alert.reason || "").toLowerCase().includes("absent");
            const isSubstitute = (alert.reason || "").toLowerCase().includes("substitute");

            return (
              <Card
                key={alert.id}
                className={`transition-all ${
                  alert.status === "Acknowledged"
                    ? "opacity-75 border-slate-200 dark:border-slate-800"
                    : isTimeout
                    ? "border-amber-300 dark:border-amber-900 bg-amber-50/20 dark:bg-amber-950/10"
                    : "border-rose-300 dark:border-rose-900 bg-rose-50/20 dark:bg-rose-950/10"
                }`}
              >
                <CardContent className="space-y-3 p-4">
                  <div className="flex items-start justify-between gap-3 border-b pb-2.5">
                    <div className="flex items-center gap-2">
                      <div
                        className={`rounded-lg p-2 ${
                          isTimeout
                            ? "bg-amber-500/10 text-amber-600"
                            : isSubstitute
                            ? "bg-blue-500/10 text-blue-600"
                            : "bg-rose-500/10 text-rose-600"
                        }`}
                      >
                        {isTimeout ? (
                          <Clock className="size-4" />
                        ) : isSubstitute ? (
                          <Info className="size-4" />
                        ) : (
                          <AlertTriangle className="size-4" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-semibold">
                          {isTimeout
                            ? "CR/LR Timeout Alert"
                            : isSubstitute
                            ? "Substitute Faculty Reported"
                            : "Faculty Absent Alert"}
                        </p>
                        <p className="text-xs text-muted-foreground">{alert.created_at ? new Date(alert.created_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" }) : `Raised at ${alert.time}`} · Asia/Kolkata</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={alert.status || "New"} />
                      {alert.status !== "Acknowledged" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleAcknowledge(alert.id)}
                          className="h-7 text-xs px-2"
                        >
                          <CheckCheck className="size-3.5 mr-1" />
                          Acknowledge
                        </Button>
                      )}
                    </div>
                  </div>

                  <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-xs">
                    <dt className="text-muted-foreground font-medium">Section:</dt>
                    <dd className="font-semibold text-primary">{alert.section}</dd>
                    <dt className="text-muted-foreground font-medium">Subject:</dt>
                    <dd className="font-medium">{alert.subject}</dd>
                    <dt className="text-muted-foreground font-medium">Session / Period:</dt>
                    <dd>{alert.session}</dd>
                    <dt className="text-muted-foreground font-medium">Reported by:</dt>
                    <dd>
                      <Badge variant="outline" className="text-[11px] font-medium">
                        {alert.reportedBy}
                      </Badge>
                    </dd>
                    <dt className="text-muted-foreground font-medium">Reason Details:</dt>
                    <dd className="text-foreground font-medium">{alert.reason}</dd>
                  </dl>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
      {!loading && !error && total > 50 && <div className="flex items-center justify-between"><p className="text-sm text-muted-foreground">Showing {(page - 1) * 50 + 1}–{Math.min(page * 50, total)} of {total}</p><div className="flex gap-2"><Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((n) => n - 1)}>Previous</Button><Button variant="outline" size="sm" disabled={page * 50 >= total} onClick={() => setPage((n) => n + 1)}>Next</Button></div></div>}
    </AdminLayout>
  );
}
