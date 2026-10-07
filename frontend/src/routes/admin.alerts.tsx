import { useState, useEffect, useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { BellRing, Download, CheckCheck, RefreshCw, Filter, AlertTriangle, Clock, UserX, Info } from "lucide-react";
import { exportToExcel } from "@/utils/exportUtils";
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
import { getAlerts, acknowledgeAlert } from "@/services/sessionService";
import type { AdminAlert } from "@/data/mock/mockData";
import { toast } from "sonner";

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

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAlerts(
        categoryFilter === ALL ? undefined : categoryFilter,
        statusFilter === ALL ? undefined : statusFilter
      );
      setAlerts(data);
    } catch (err: any) {
      setError(err.message || "Failed to load notifications and alerts.");
      toast.error(err.message || "Failed to load notifications and alerts.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [categoryFilter, statusFilter]);

  const handleAcknowledge = async (alertId: string) => {
    try {
      await acknowledgeAlert(alertId);
      toast.success("Alert acknowledged.");
      await loadData();
    } catch (err: any) {
      toast.error(err.message || "Failed to acknowledge alert.");
    }
  };

  const filteredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      if (statusFilter !== ALL) {
        if ((a.status || "New").toLowerCase() !== statusFilter.toLowerCase()) {
          return false;
        }
      }
      if (categoryFilter !== ALL) {
        const reasonLower = (a.reason || "").toLowerCase();
        if (categoryFilter === "NO_RESPONSE_10MIN") {
          if (!reasonLower.includes("10 min") && !reasonLower.includes("no response")) return false;
        } else if (categoryFilter === "FACULTY_ABSENT") {
          if (!reasonLower.includes("not available") && !reasonLower.includes("absent") && !reasonLower.includes("substitute")) return false;
        } else if (categoryFilter === "FACULTY_STATUS_UPDATED") {
          if (!reasonLower.includes("update") && !reasonLower.includes("status")) return false;
        }
      }
      return true;
    });
  }, [alerts, categoryFilter, statusFilter]);

  const handleExport = () => {
    const exportData = filteredAlerts.map((a) => ({
      "Alert Time": a.time,
      Section: a.section,
      Subject: a.subject,
      Session: a.session,
      "Reported By": a.reportedBy,
      Status: a.status || "New",
      Reason: a.reason,
    }));
    exportToExcel(exportData, "Attendance_Alerts_Log");
    toast.success("Alerts exported successfully.");
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
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={filteredAlerts.length === 0}
              className="bg-emerald-600/10 text-emerald-600 hover:bg-emerald-600/20 border-emerald-500/30"
            >
              <Download className="size-4 mr-2" />
              Export Alerts
            </Button>
          </div>
        }
      />

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center gap-3 bg-card p-4 rounded-xl border shadow-sm">
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
                        <p className="text-xs text-muted-foreground">Raised at {alert.time}</p>
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
    </AdminLayout>
  );
}
