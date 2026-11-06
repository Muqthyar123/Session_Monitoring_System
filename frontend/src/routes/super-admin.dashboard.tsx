import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Building2,
  GitBranch,
  UserCheck,
  Users,
  GraduationCap,
  RefreshCw,
  Plus,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import { SuperAdminLayout } from "@/layouts/SuperAdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { LoadingState, ErrorState } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getSuperAdminDashboard } from "@/services/superAdminService";

export const Route = createFileRoute("/super-admin/dashboard")({
  head: () => ({
    meta: [
      { title: "Super Admin Dashboard — Multi-Branch Control" },
      { name: "description", content: "Executive overview of all campuses, branches, HODs, mentors, and students." },
      { property: "og:title", content: "Super Admin Dashboard — Multi-Branch Control" },
      { property: "og:description", content: "Executive overview of all campuses, branches, HODs, mentors, and students." },
    ],
  }),
  component: SuperAdminDashboardPage,
});

function SuperAdminDashboardPage() {
  const { data, loading, error, reload } = useAsyncData(
    () => getSuperAdminDashboard(),
    [],
    30000 // auto-refresh every 30 seconds
  );

  const today = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date());

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <PageHeader
            title="Super Admin Dashboard"
            description={`Master multi-branch intelligence • ${today}`}
          />
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={reload}
              disabled={loading}
              className="gap-1.5 text-xs cursor-pointer"
            >
              <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Link to="/super-admin/branches">
              <Button size="sm" className="gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-xs text-white cursor-pointer">
                <Plus className="size-3.5" />
                Add Branch
              </Button>
            </Link>
          </div>
        </div>

        {/* Loading / Error States */}
        {loading && !data && <LoadingState label="Loading multi-branch metrics..." />}
        {error && !data && <ErrorState message={error ?? undefined} onRetry={reload} />}

        {data && (
          <>
            {/* Top Stat Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <StatCard
                label="Total Campuses"
                value={data.total_sites ?? data.totalSites ?? 0}
                icon={Building2}
                hint="Registered sites"
                tone="info"
              />
              <StatCard
                label="Total Branches"
                value={data.total_branches ?? data.totalBranches ?? 0}
                icon={GitBranch}
                hint="Active departments"
                tone="default"
              />
              <StatCard
                label="Branch HODs"
                value={data.total_hods ?? data.totalHods ?? 0}
                icon={UserCheck}
                hint="Assigned administrators"
                tone="success"
              />
              <StatCard
                label="Total Mentors"
                value={data.total_mentors ?? data.totalMentors ?? 0}
                icon={GraduationCap}
                hint="Across all branches"
                tone="warning"
              />
              <StatCard
                label="Total Students"
                value={data.total_students ?? data.totalStudents ?? 0}
                icon={Users}
                hint="Enrolled institutional count"
                tone="info"
              />
            </div>

            {/* Branch-wise Detailed Statistics Table */}
            <Card className="border-border">
              <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4">
                <div>
                  <CardTitle className="text-base font-bold text-foreground">
                    Branch-Wise Statistics &amp; HOD Assignments
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Comprehensive overview of all academic departments and personnel distribution
                  </CardDescription>
                </div>
                <Link to="/super-admin/branches">
                  <Button variant="ghost" size="sm" className="gap-1 text-xs text-indigo-600 hover:text-indigo-700">
                    Manage Branches <ArrowRight className="size-3" />
                  </Button>
                </Link>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-border bg-muted/40 text-muted-foreground uppercase tracking-wider text-[11px] font-semibold">
                        <th className="py-3 px-4">Branch Code &amp; Name</th>
                        <th className="py-3 px-4">Campus / Site</th>
                        <th className="py-3 px-4">Assigned HOD</th>
                        <th className="py-3 px-4 text-center">Sections</th>
                        <th className="py-3 px-4 text-center">Mentors</th>
                        <th className="py-3 px-4 text-center">Students</th>
                        <th className="py-3 px-4 text-center">Status</th>
                        <th className="py-3 px-4 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {(!data.branch_stats || data.branch_stats.length === 0) ? (
                        <tr>
                          <td colSpan={8} className="py-8 text-center text-muted-foreground">
                            No branches configured yet. Click "Add Branch" to create one.
                          </td>
                        </tr>
                      ) : (
                        data.branch_stats.map((b) => (
                          <tr key={b.id} className="hover:bg-muted/20 transition-colors">
                            <td className="py-3 px-4">
                              <div className="font-bold text-foreground flex items-center gap-2">
                                <Badge variant="outline" className="font-mono bg-background text-indigo-600 border-indigo-200">
                                  {b.code}
                                </Badge>
                                <span className="font-semibold">{b.name}</span>
                              </div>
                            </td>
                            <td className="py-3 px-4 text-muted-foreground">
                              {b.site_name || "Main Campus"}
                            </td>
                            <td className="py-3 px-4">
                              {b.hod_name && b.hod_name !== "Unassigned" ? (
                                <div className="space-y-0.5">
                                  <div className="font-medium text-foreground flex items-center gap-1.5">
                                    <ShieldCheck className="size-3.5 text-emerald-600" />
                                    <span>{b.hod_name}</span>
                                  </div>
                                  <div className="text-[11px] text-muted-foreground">{b.hod_email}</div>
                                </div>
                              ) : (
                                <Badge variant="secondary" className="bg-amber-100 text-amber-800 border border-amber-200 gap-1 text-[10px]">
                                  <AlertCircle className="size-3" /> Unassigned
                                </Badge>
                              )}
                            </td>
                            <td className="py-3 px-4 text-center font-medium">
                              {b.section_count}
                            </td>
                            <td className="py-3 px-4 text-center font-medium text-indigo-600">
                              {b.mentor_count}
                            </td>
                            <td className="py-3 px-4 text-center font-bold text-emerald-600">
                              {b.student_count}
                            </td>
                            <td className="py-3 px-4 text-center">
                              {b.is_active ? (
                                <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-0 text-[10px]">
                                  Active
                                </Badge>
                              ) : (
                                <Badge variant="secondary" className="text-[10px]">
                                  Inactive
                                </Badge>
                              )}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <Link
                                to="/super-admin/branches"
                                className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                              >
                                View <ExternalLink className="size-3" />
                              </Link>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

            {/* Bottom Row: Recent Branches & Recent HODs */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Recent Branches */}
              <Card className="border-border">
                <CardHeader className="flex flex-row items-center justify-between pb-3">
                  <div>
                    <CardTitle className="text-sm font-bold">Recently Created Branches</CardTitle>
                    <CardDescription className="text-xs">Latest departments added to the system</CardDescription>
                  </div>
                  <Link to="/super-admin/branches" className="text-xs text-indigo-600 hover:underline">
                    View all
                  </Link>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(!data.recent_branches || data.recent_branches.length === 0) ? (
                    <p className="text-xs text-muted-foreground py-4 text-center">No recent branches</p>
                  ) : (
                    data.recent_branches.map((rb) => (
                      <div
                        key={rb.id}
                        className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-muted/20"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex size-8 items-center justify-center rounded-md bg-indigo-500/10 text-indigo-600 font-bold text-xs font-mono">
                            {rb.code}
                          </div>
                          <div>
                            <div className="text-xs font-bold text-foreground">{rb.name}</div>
                            <div className="text-[11px] text-muted-foreground">{rb.site_name || "Main Campus"}</div>
                          </div>
                        </div>
                        {rb.created_at && (
                          <span className="text-[10px] text-muted-foreground">
                            {new Date(rb.created_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              {/* Recent HODs */}
              <Card className="border-border">
                <CardHeader className="flex flex-row items-center justify-between pb-3">
                  <div>
                    <CardTitle className="text-sm font-bold">Recently Created HODs</CardTitle>
                    <CardDescription className="text-xs">Newly provisioned branch administrators</CardDescription>
                  </div>
                  <Link to="/super-admin/hods" className="text-xs text-indigo-600 hover:underline">
                    View all
                  </Link>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(!data.recent_hods || data.recent_hods.length === 0) ? (
                    <p className="text-xs text-muted-foreground py-4 text-center">No recent HOD accounts</p>
                  ) : (
                    data.recent_hods.map((rh) => (
                      <div
                        key={rh.id}
                        className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-muted/20"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex size-8 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-600 font-bold text-xs">
                            <ShieldCheck className="size-4" />
                          </div>
                          <div>
                            <div className="text-xs font-bold text-foreground">{rh.name}</div>
                            <div className="text-[11px] text-muted-foreground">{rh.email}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {rh.branch_code && (
                            <Badge variant="outline" className="font-mono text-[10px] text-indigo-600">
                              {rh.branch_code}
                            </Badge>
                          )}
                          {rh.created_at && (
                            <span className="text-[10px] text-muted-foreground">
                              {new Date(rh.created_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </SuperAdminLayout>
  );
}
