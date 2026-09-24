import { useState, useMemo } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  BookOpen,
  CheckCircle2,
  Clock,
  Filter,
  GraduationCap,
  Layers,
  Repeat2,
  Search,
  UserCheck,
  UserX,
  XCircle,
  AlertCircle,
  RefreshCw,
  ArrowLeft,
  Calendar,
  ChevronRight,
} from "lucide-react";
import { AdminLayout } from "@/layouts/AdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getAdminDashboard } from "@/services/sessionService";

export const Route = createFileRoute("/admin/analytics")({
  head: () => ({
    meta: [
      { title: "Faculty Analytics — Admin Portal" },
      { name: "description", content: "Yearly summary cards, section cards, faculty attendance metrics, and global faculty search." },
      { property: "og:title", content: "Faculty Analytics — Admin Portal" },
      { property: "og:description", content: "Comprehensive faculty attendance metrics across sections and academic years." },
    ],
  }),
  component: AdminAnalyticsPage,
});

interface SectionCardItem {
  section: string;
  year: string;
  totalClasses: number;
  facultyCount: number;
  present: number;
  absent: number;
  substitute: number;
  late: number;
  presencePercent: number;
}

interface YearCardItem {
  year: string;
  totalSections: number;
  totalClasses: number;
  facultyCount: number;
  present: number;
  absent: number;
  substitute: number;
  late: number;
  presencePercent: number;
  sections: SectionCardItem[];
}

interface FacultyAnalyticsItem {
  facultyName: string;
  subject: string;
  section: string;
  year?: string;
  totalClasses: number;
  attendedClasses: number;
  absentClasses: number;
  lateClasses?: number;
  substitutedClasses: number;
  totalHours: number;
  attendedHours: number;
  absentHours: number;
  lateHours?: number;
  substitutedHours: number;
  attendancePercentage: number;
}

function AdminAnalyticsPage() {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsyncData(() => getAdminDashboard(), [], 3000);

  const [selectedYear, setSelectedYear] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeSearch, setActiveSearch] = useState("");

  const rawYearCards: YearCardItem[] = data?.yearCards ?? [];
  const rawSectionCards: SectionCardItem[] = data?.sectionsCards ?? [];
  const facultyList: FacultyAnalyticsItem[] = data?.facultyAnalytics ?? [];

  // Fallback: If backend sends sectionsCards but not yearCards, construct yearCards dynamically
  const yearCards: YearCardItem[] = useMemo(() => {
    if (rawYearCards.length > 0) return rawYearCards;
    if (rawSectionCards.length === 0) return [];

    const map = new Map<string, SectionCardItem[]>();
    rawSectionCards.forEach((sc) => {
      const yr = sc.year || "2nd Year";
      if (!map.has(yr)) map.set(yr, []);
      map.get(yr)!.push(sc);
    });

    return Array.from(map.entries()).map(([yr, secs]) => {
      const tot = secs.reduce((acc, curr) => acc + curr.totalClasses, 0);
      const pres = secs.reduce((acc, curr) => acc + curr.present, 0);
      const abs = secs.reduce((acc, curr) => acc + curr.absent, 0);
      const sub = secs.reduce((acc, curr) => acc + curr.substitute, 0);
      const late = secs.reduce((acc, curr) => acc + curr.late, 0);
      const evalCount = pres + abs + sub;
      const pct = evalCount > 0 ? Math.round((pres / evalCount) * 1000) / 10 : 100.0;
      const facSet = new Set(secs.map((s) => s.facultyCount));

      return {
        year: yr,
        totalSections: secs.length,
        totalClasses: tot,
        facultyCount: Math.max(facSet.size, 1),
        present: pres,
        absent: abs,
        substitute: sub,
        late: late,
        presencePercent: pct,
        sections: secs,
      };
    });
  }, [rawYearCards, rawSectionCards]);

  // Selected year object (for Level 2 Section Cards view)
  const activeYearObj = useMemo(() => {
    if (!selectedYear) return null;
    return yearCards.find((y) => y.year === selectedYear) || null;
  }, [selectedYear, yearCards]);

  // Execute Search
  const handleSearchSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setActiveSearch(searchQuery.trim());
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    setActiveSearch("");
  };

  // Filter faculty based on selected section, selected year, or global search query
  const filteredFaculty = useMemo(() => {
    let result = [...facultyList];

    if (activeSearch) {
      const queryLower = activeSearch.toLowerCase();
      result = result.filter(
        (f) =>
          f.facultyName.toLowerCase().includes(queryLower) ||
          f.subject.toLowerCase().includes(queryLower)
      );
    } else if (selectedSection) {
      result = result.filter(
        (f) => f.section.toUpperCase() === selectedSection.toUpperCase()
      );
    } else if (selectedYear) {
      const validSecs = new Set(
        (activeYearObj?.sections ?? []).map((s) => s.section.toUpperCase())
      );
      result = result.filter(
        (f) =>
          (f.year && f.year === selectedYear) ||
          (f.section && validSecs.has(f.section.toUpperCase()))
      );
    }

    return result;
  }, [facultyList, selectedSection, selectedYear, activeYearObj, activeSearch]);

  // Calculate cumulative stats for active selection/search
  const cumulativeSummary = useMemo(() => {
    const list = filteredFaculty;
    const tot = list.reduce((acc, curr) => acc + (curr.totalClasses || curr.totalHours || 0), 0);
    const att = list.reduce((acc, curr) => acc + (curr.attendedClasses || curr.attendedHours || 0), 0);
    const abs = list.reduce((acc, curr) => acc + (curr.absentClasses || curr.absentHours || 0), 0);
    const late = list.reduce((acc, curr) => acc + (curr.lateClasses || curr.lateHours || 0), 0);
    const sub = list.reduce((acc, curr) => acc + (curr.substitutedClasses || curr.substitutedHours || 0), 0);
    const evaluated = att + abs + sub;
    const pct = evaluated > 0 ? Math.round((att / evaluated) * 1000) / 10 : 100.0;

    return {
      totalClasses: tot,
      attendedClasses: att,
      absentClasses: abs,
      lateClasses: late,
      substitutedClasses: sub,
      presencePercent: pct,
    };
  }, [filteredFaculty]);

  return (
    <AdminLayout>
      <PageHeader
        title="Faculty Analytics & Section Summaries"
        description="Overall year summaries, per-section faculty attendance metrics, and global faculty search."
        actions={
          <Button variant="outline" size="sm" onClick={reload}>
            <RefreshCw className="size-4 mr-1.5" /> Refresh Metrics
          </Button>
        }
      />

      {loading ? (
        <LoadingState rows={4} label="Loading faculty analytics..." />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : (
        <div className="space-y-6">
          {/* Global Faculty Search Bar */}
          <Card id="faculty-search" className="border-indigo-100 bg-slate-50/80 dark:border-indigo-950 dark:bg-slate-900/50">
            <CardContent className="p-4 sm:p-5">
              <form onSubmit={handleSearchSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="relative flex-1">
                  <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    type="text"
                    placeholder="Search faculty name (e.g. Ch.Revathi or Dr. Ramesh) across all sections & years..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-800"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-5">
                    <Search className="size-4 mr-1.5" /> Search Faculty
                  </Button>
                  {(activeSearch || searchQuery) ? (
                    <Button type="button" variant="outline" onClick={handleClearSearch}>
                      Clear
                    </Button>
                  ) : null}
                </div>
              </form>

              {activeSearch ? (
                <div className="mt-3 flex items-center gap-2 text-xs font-semibold text-indigo-700 dark:text-indigo-300">
                  <Filter className="size-3.5" />
                  <span>
                    Showing cumulative summary across all sections & years for faculty matching: &quot;{activeSearch}&quot;
                  </span>
                  <Badge variant="outline" className="ml-auto cursor-pointer" onClick={handleClearSearch}>
                    Reset Search
                  </Badge>
                </div>
              ) : null}
            </CardContent>
          </Card>

          {/* Cards Display Section (Year Cards -> Section Cards Hierarchy) */}
          {!activeSearch ? (
            <section className="space-y-4">
              {yearCards.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-800">
                  <Calendar className="mx-auto size-8 text-slate-400 mb-2" />
                  <p className="font-semibold text-slate-700 dark:text-slate-300">No Timetables Uploaded</p>
                  <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                    Year and section cards are created automatically when timetables are uploaded into MongoDB.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4"
                    onClick={() => navigate({ to: "/admin/timetable" })}
                  >
                    Go to Timetable Management
                  </Button>
                </div>
              ) : !selectedYear ? (
                /* LEVEL 1 VIEW: Year Cards Overview */
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <Layers className="size-5 text-indigo-600 dark:text-indigo-400" />
                        Academic Years Overview (Cards by Year)
                      </h2>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Click on any academic year card below to view its section-wise details and breakdown.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {yearCards.map((yc) => (
                      <div
                        key={yc.year}
                        onClick={() => {
                          setSelectedYear(yc.year);
                          setSelectedSection(null);
                        }}
                        className="group cursor-pointer rounded-xl border border-slate-200 bg-white p-5 transition-all hover:border-indigo-400 hover:shadow-lg dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
                      >
                        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
                          <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                              Academic Year
                            </span>
                            <h3 className="text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                              {yc.year}
                            </h3>
                          </div>
                          <div className="text-right">
                            <span className="inline-block rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                              {yc.totalSections} {yc.totalSections === 1 ? "Section" : "Sections"}
                            </span>
                            <div className="mt-1">
                              <span className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-bold ${
                                yc.presencePercent >= 85
                                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                  : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                              }`}>
                                {yc.presencePercent}% Present
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="mt-3.5 grid grid-cols-2 gap-2 text-xs">
                          <div className="text-slate-600 dark:text-slate-400">
                            Total Hours: <span className="font-semibold text-slate-900 dark:text-white">{yc.totalClasses}</span>
                          </div>
                          <div className="text-slate-600 dark:text-slate-400">
                            Faculty Count: <span className="font-semibold text-slate-900 dark:text-white">{yc.facultyCount}</span>
                          </div>
                          <div className="text-emerald-600 dark:text-emerald-400 font-medium">
                            Present: <span className="font-bold">{yc.present}</span>
                          </div>
                          <div className="text-rose-600 dark:text-rose-400 font-medium">
                            Absent: <span className="font-bold">{yc.absent}</span>
                          </div>
                          <div className="text-amber-600 dark:text-amber-400 font-medium">
                            Late: <span className="font-bold">{yc.late}</span>
                          </div>
                          <div className="text-blue-600 dark:text-blue-400 font-medium">
                            Substitute: <span className="font-bold">{yc.substitute}</span>
                          </div>
                        </div>

                        <div className="mt-4 flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800/80 text-xs font-semibold text-indigo-600 dark:text-indigo-400 group-hover:translate-x-1 transition-transform">
                          <span>View Sections ({yc.totalSections})</span>
                          <ChevronRight className="size-4" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                /* LEVEL 2 VIEW: Section Cards for Selected Year */
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-3 dark:border-slate-800">
                    <div className="flex items-center gap-3">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedYear(null);
                          setSelectedSection(null);
                        }}
                        className="text-slate-700 dark:text-slate-300"
                      >
                        <ArrowLeft className="size-4 mr-1.5" /> Back to All Years
                      </Button>
                      <div>
                        <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                          <Layers className="size-5 text-indigo-600 dark:text-indigo-400" />
                          Sections for {selectedYear}
                        </h2>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          Click any section card below to view detailed faculty summary for that section only.
                        </p>
                      </div>
                    </div>
                    {selectedSection ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedSection(null)}
                        className="text-indigo-600 dark:text-indigo-400"
                      >
                        Show All Sections in {selectedYear}
                      </Button>
                    ) : null}
                  </div>

                  <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {(activeYearObj?.sections ?? []).map((sc) => {
                      const isSelected = selectedSection === sc.section;
                      return (
                        <div
                          key={sc.section}
                          onClick={() => {
                            setSelectedSection(isSelected ? null : sc.section);
                          }}
                          className={`group cursor-pointer rounded-xl border p-4 transition-all ${
                            isSelected
                              ? "border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-500/20 dark:border-indigo-500 dark:bg-indigo-950/40"
                              : "border-slate-200 bg-white hover:border-indigo-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
                          }`}
                        >
                          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 dark:border-slate-800">
                            <div>
                              <h4 className="text-base font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                                Section {sc.section}
                              </h4>
                              <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                                {sc.year}
                              </span>
                            </div>
                            <span
                              className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                                sc.presencePercent >= 85
                                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                  : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                              }`}
                            >
                              {sc.presencePercent}% Present
                            </span>
                          </div>

                          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                            <div className="text-slate-600 dark:text-slate-400">
                              Total Classes:{" "}
                              <span className="font-semibold text-slate-900 dark:text-white">
                                {sc.totalClasses}
                              </span>
                            </div>
                            <div className="text-slate-600 dark:text-slate-400">
                              Faculty Count:{" "}
                              <span className="font-semibold text-slate-900 dark:text-white">
                                {sc.facultyCount}
                              </span>
                            </div>
                            <div className="text-emerald-600 dark:text-emerald-400 font-medium">
                              Present: <span className="font-bold">{sc.present}</span>
                            </div>
                            <div className="text-rose-600 dark:text-rose-400 font-medium">
                              Absent: <span className="font-bold">{sc.absent}</span>
                            </div>
                            <div className="text-amber-600 dark:text-amber-400 font-medium">
                              Late: <span className="font-bold">{sc.late}</span>
                            </div>
                            <div className="text-blue-600 dark:text-blue-400 font-medium">
                              Substitute: <span className="font-bold">{sc.substitute}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </section>
          ) : null}

          {/* Metric Overview Cards for Active Selection or Search */}
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <StatCard label="Total Classes" value={cumulativeSummary.totalClasses} icon={Clock} />
            <StatCard label="Classes Present" value={cumulativeSummary.attendedClasses} icon={UserCheck} tone="success" />
            <StatCard label="Classes Absent" value={cumulativeSummary.absentClasses} icon={UserX} tone="destructive" />
            <StatCard label="Late Arrivals" value={cumulativeSummary.lateClasses} icon={AlertCircle} tone="warning" />
            <StatCard label="Substitute Classes" value={cumulativeSummary.substitutedClasses} icon={Repeat2} tone="info" />
          </section>

          {/* Faculty Summary Table */}
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <GraduationCap className="size-5 text-indigo-600 dark:text-indigo-400" />
                  {activeSearch
                    ? `Faculty Cumulative Summary: "${activeSearch}"`
                    : selectedSection
                    ? `Faculty Summary for Section ${selectedSection} Only`
                    : selectedYear
                    ? `Faculty Summary for ${selectedYear}`
                    : "All Faculty Attendance Summaries"}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {activeSearch
                    ? "Cumulative summary across all sections & years for matching faculty."
                    : selectedSection
                    ? `Showing faculty summary for section ${selectedSection} only.`
                    : selectedYear
                    ? `Showing faculty summary for ${selectedYear} across all sections.`
                    : "Summary of present, absent, late, and substitute classes for all faculty members."}
                </p>
              </div>

              {(selectedSection || selectedYear || activeSearch) ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setSelectedYear(null);
                    setSelectedSection(null);
                    handleClearSearch();
                  }}
                  className="text-xs"
                >
                  Reset Selection Filter
                </Button>
              ) : null}
            </div>

            {filteredFaculty.length === 0 ? (
              <div className="py-12 text-center text-sm text-slate-500 dark:text-slate-400">
                No faculty attendance records found matching current selection.
              </div>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-700 dark:text-slate-300">
                  <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-3">Faculty Member</th>
                      <th className="px-4 py-3">Subject(s)</th>
                      <th className="px-4 py-3">Year / Section</th>
                      <th className="px-4 py-3 text-center">Total Classes</th>
                      <th className="px-4 py-3 text-center">Present</th>
                      <th className="px-4 py-3 text-center">Absent</th>
                      <th className="px-4 py-3 text-center">Late</th>
                      <th className="px-4 py-3 text-center">Substitute</th>
                      <th className="px-4 py-3 text-right">Attendance %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                    {filteredFaculty.map((fac, idx) => {
                      const pct = fac.attendancePercentage;
                      const badgeColor =
                        pct >= 85
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                          : pct >= 70
                          ? "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
                          : "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400";

                      const barColor =
                        pct >= 85 ? "bg-emerald-500" : pct >= 70 ? "bg-amber-500" : "bg-rose-500";

                      const totalCls = fac.totalClasses || fac.totalHours;
                      const attCls = fac.attendedClasses || fac.attendedHours;
                      const absCls = fac.absentClasses || fac.absentHours;
                      const lateCls = fac.lateClasses || fac.lateHours || 0;
                      const subCls = fac.substitutedClasses || fac.substitutedHours;

                      return (
                        <tr
                          key={`${fac.facultyName}-${fac.section}-${idx}`}
                          className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                        >
                          <td className="px-4 py-3.5 font-medium text-slate-900 dark:text-white">
                            <div className="flex items-center gap-2">
                              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-50 text-xs font-bold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                                {fac.facultyName.charAt(0).toUpperCase()}
                              </div>
                              <span>{fac.facultyName}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                              <BookOpen className="h-3.5 w-3.5 text-slate-400" />
                              <span>{fac.subject}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3.5">
                            <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                              {fac.year ? `${fac.year} · ` : ""}{fac.section}
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-center font-semibold text-slate-900 dark:text-white">
                            <div className="inline-flex items-center gap-1">
                              <Clock className="h-3.5 w-3.5 text-slate-400" />
                              <span>{totalCls} classes</span>
                            </div>
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400">
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              {attCls} classes
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700 dark:bg-rose-950/40 dark:text-rose-400">
                              <XCircle className="h-3.5 w-3.5" />
                              {absCls} classes
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
                              <AlertCircle className="h-3.5 w-3.5" />
                              {lateCls} classes
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-950/40 dark:text-blue-400">
                              <Repeat2 className="h-3.5 w-3.5" />
                              {subCls} classes
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="w-16 rounded-full bg-slate-100 dark:bg-slate-800">
                                <div
                                  className={`h-1.5 rounded-full ${barColor}`}
                                  style={{ width: `${Math.min(100, pct)}%` }}
                                />
                              </div>
                              <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-bold ${badgeColor}`}>
                                {pct}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </AdminLayout>
  );
}
