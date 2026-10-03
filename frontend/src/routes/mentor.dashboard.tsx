import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Users,
  UserX,
  GraduationCap,
  Layers,
  ChevronRight,
  BarChart3,
  Calendar,
  Phone,
  Mail,
  Building,
  UserCheck,
  RotateCcw,
} from "lucide-react";
import { MentorLayout } from "@/layouts/MentorLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getMentorDashboard } from "@/services/mentorService";

export const Route = createFileRoute("/mentor/dashboard")({
  head: () => ({
    meta: [
      { title: "Mentor Dashboard — Session Monitoring System" },
      { name: "description", content: "Comprehensive overview of enrolled students, today's absentees, and class monitoring." },
    ],
  }),
  component: MentorDashboardPage,
});

function MentorDashboardPage() {
  const { data, loading, error, reload } = useAsyncData(() => getMentorDashboard(), [], 15000);

  const todayStr = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <MentorLayout>
      <PageHeader
        title="Mentor Dashboard"
        description={`Today is ${todayStr}. Overview of enrolled students and daily absentee tracking.`}
        actions={
          <Button variant="outline" size="sm" onClick={reload}>
            <RotateCcw className="size-4 mr-2" /> Refresh
          </Button>
        }
      />

      {loading ? (
        <LoadingState label="Loading mentor dashboard statistics..." />
      ) : error ? (
        <ErrorState title="Failed to load dashboard" description={error.message} retry={reload} />
      ) : data ? (
        <div className="space-y-6">
          {/* Mentor Profile Overview Banner */}
          <Card className="border-emerald-500/20 bg-gradient-to-r from-emerald-50/50 via-background to-teal-50/30 dark:from-emerald-950/20 dark:to-teal-950/10">
            <CardHeader className="pb-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-600 text-white font-bold text-lg shadow-sm">
                    {data.mentorInfo.name ? data.mentorInfo.name.charAt(0).toUpperCase() : "M"}
                  </div>
                  <div>
                    <CardTitle className="text-lg font-bold flex items-center gap-2">
                      {data.mentorInfo.name}
                      <Badge variant="outline" className="bg-emerald-100/80 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200 border-emerald-300 text-[11px]">
                        {data.mentorInfo.designation || "Faculty Mentor"}
                      </Badge>
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Faculty / Mentor ID: <span className="font-mono font-semibold text-foreground">{data.mentorInfo.mentorId || "—"}</span>
                    </CardDescription>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  {data.mentorInfo.department && (
                    <span className="flex items-center gap-1 bg-background px-2.5 py-1 rounded-md border">
                      <Building className="size-3.5 text-primary" /> {data.mentorInfo.department}
                    </span>
                  )}
                  {data.mentorInfo.email && (
                    <span className="flex items-center gap-1 bg-background px-2.5 py-1 rounded-md border">
                      <Mail className="size-3.5 text-primary" /> {data.mentorInfo.email}
                    </span>
                  )}
                  {data.mentorInfo.phone && (
                    <a
                      href={`tel:${data.mentorInfo.phone}`}
                      className="flex items-center gap-1 bg-background px-2.5 py-1 rounded-md border text-primary hover:underline font-mono"
                    >
                      <Phone className="size-3.5" /> {data.mentorInfo.phone}
                    </a>
                  )}
                </div>
              </div>
            </CardHeader>
          </Card>

          {/* Key Summary Stat Cards */}
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Total Enrolled Students"
              value={data.totalStudents}
              icon={Users}
            />
            <StatCard
              label="Today's Absentees"
              value={data.totalAbsenteesToday}
              icon={UserX}
              tone={data.totalAbsenteesToday > 0 ? "destructive" : "success"}
            />
            <StatCard
              label="Monitored Academic Years"
              value={data.yearCounts.length}
              icon={GraduationCap}
            />
            <StatCard
              label="Monitored Sections"
              value={data.sectionCounts.length}
              icon={Layers}
            />
          </section>

          {/* Primary Quick Access Hub */}
          <div className="grid gap-4 md:grid-cols-3">
            <Link to="/mentor/students" className="block group">
              <Card className="h-full transition-all hover:border-primary hover:shadow-md">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-bold flex items-center gap-2">
                      <Users className="size-5 text-primary" /> All Students Directory
                    </CardTitle>
                    <ChevronRight className="size-4 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                  <CardDescription className="text-xs">
                    Browse all enrolled students organized by Year &amp; Section, or perform a global student search.
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-primary">
                    <span>{data.totalStudents} Total Students</span>
                    <span className="flex items-center">Open Directory <ChevronRight className="size-3.5 ml-0.5" /></span>
                  </div>
                </CardContent>
              </Card>
            </Link>

            <Link to="/mentor/absentees" className="block group">
              <Card className="h-full transition-all hover:border-rose-500 hover:shadow-md">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-bold flex items-center gap-2 text-rose-600 dark:text-rose-400">
                      <UserX className="size-5" /> Today's Absentees
                    </CardTitle>
                    <ChevronRight className="size-4 text-muted-foreground group-hover:text-rose-500 transition-colors" />
                  </div>
                  <CardDescription className="text-xs">
                    Inspect today's absent students, place one-click dialer phone calls, and record absence follow-up notes.
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-rose-600 dark:text-rose-400">
                    <span>{data.totalAbsenteesToday} Reported Absent</span>
                    <span className="flex items-center">Inspect Absentees <ChevronRight className="size-3.5 ml-0.5" /></span>
                  </div>
                </CardContent>
              </Card>
            </Link>

            <Link to="/mentor/analytics" className="block group">
              <Card className="h-full transition-all hover:border-blue-500 hover:shadow-md">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-bold flex items-center gap-2 text-blue-600 dark:text-blue-400">
                      <BarChart3 className="size-5" /> Attendance Analytics
                    </CardTitle>
                    <ChevronRight className="size-4 text-muted-foreground group-hover:text-blue-500 transition-colors" />
                  </div>
                  <CardDescription className="text-xs">
                    View student attendance percentages, frequent absentees, and complete historical audit logs.
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-blue-600 dark:text-blue-400">
                    <span>Longitudinal Tracking</span>
                    <span className="flex items-center">View Analytics <ChevronRight className="size-3.5 ml-0.5" /></span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          </div>

          {/* Academic Years Breakdown */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground">
              Academic Year Enrollment &amp; Today's Absence Summary
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {data.yearCounts.map((yc) => (
                <Link
                  key={yc.year}
                  to="/mentor/students"
                  className="block group"
                >
                  <Card className="transition-all hover:border-primary hover:shadow-sm">
                    <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                      <CardTitle className="text-base font-bold">{yc.year}</CardTitle>
                      <GraduationCap className="size-5 text-muted-foreground group-hover:text-primary transition-colors" />
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-muted-foreground">Enrolled Students:</span>
                        <span className="font-bold text-foreground">{yc.studentCount}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-muted-foreground">Today's Absentees:</span>
                        <Badge variant={yc.absenteeCount > 0 ? "destructive" : "outline"} className="text-[10px] px-1.5 py-0">
                          {yc.absenteeCount} absent
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </MentorLayout>
  );
}
