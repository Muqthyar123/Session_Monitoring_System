import { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { downloadAbsenteeHistory } from "@/services/studentAttendanceService";
import {
  getMentorAbsenteesSections,
  getMentorAbsenteesYears,
  getMentorStudentsSections,
  getMentorStudentsYears,
} from "@/services/mentorService";

type YearOption = { year: string };
type SectionOption = { section: string };

export function HistoryExportToolbar({ year, section, role }: { year?: string | null; section?: string | null; role: "ADMIN" | "MENTOR" }) {
  const [years, setYears] = useState<YearOption[]>([]);
  const [sections, setSections] = useState<SectionOption[]>([]);
  const [selectedYear, setSelectedYear] = useState(year || "");
  const [selectedSection, setSelectedSection] = useState(section || "");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [branch, setBranch] = useState("");
  const [format, setFormat] = useState<"pdf" | "xlsx" | "csv">("pdf");
  const [loading, setLoading] = useState(false);

  useEffect(() => { setSelectedYear(year || ""); }, [year]);
  useEffect(() => { setSelectedSection(section || ""); }, [section]);

  useEffect(() => {
    let active = true;
    const loadYears = role === "MENTOR" ? getMentorStudentsYears() : getMentorAbsenteesYears();
    loadYears.then((items) => {
      if (active) setYears(items.map((item) => ({ year: item.year })).filter((item) => item.year));
    }).catch((error: any) => toast.error(error.message || "Could not load academic years."));
    return () => { active = false; };
  }, [role]);

  useEffect(() => {
    let active = true;
    setSections([]);
    if (!selectedYear) return;
    const loadSections = role === "MENTOR"
      ? getMentorStudentsSections(selectedYear)
      : getMentorAbsenteesSections(selectedYear);
    loadSections.then((items) => {
      if (active) setSections(items.map((item) => ({ section: item.section })).filter((item) => item.section));
    }).catch((error: any) => toast.error(error.message || "Could not load sections for this year."));
    return () => { active = false; };
  }, [role, selectedYear]);

  const uniqueSections = useMemo(() => [...new Map(sections.map((item) => [item.section.toUpperCase(), item])).values()], [sections]);

  const exportHistory = async () => {
    if (!selectedYear) { toast.error("Select an academic year before exporting."); return; }
    if (fromDate && toDate && fromDate > toDate) { toast.error("From Date cannot be later than To Date."); return; }
    setLoading(true);
    try {
      await downloadAbsenteeHistory({ format, year: selectedYear, section: selectedSection || undefined, branch: branch.trim() || undefined, rollNumber: rollNumber.trim() || undefined, fromDate: fromDate || undefined, toDate: toDate || undefined });
      toast.success("History export downloaded.");
    } catch (error: any) { toast.error(error.message || "History export failed."); }
    finally { setLoading(false); }
  };

  return (
    <Card className="my-4 border-primary/20">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base"><Download className="size-4" />Export absentee history</CardTitle>
        <CardDescription>
          {role === "ADMIN" ? "Download attendance history for an academic year, section, or student." : "Download history only for students assigned to your mentor account."}
          {" "}Choose All Sections for the whole academic year. Leave both dates empty for all available history; date filters use attendance dates in Asia/Kolkata.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 items-end gap-x-4 gap-y-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="min-w-0 space-y-1.5"><Label htmlFor="history-year">Academic year</Label><select id="history-year" className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={selectedYear} onChange={(event) => { setSelectedYear(event.target.value); setSelectedSection(""); }}><option value="">Select academic year</option>{years.map((item) => <option key={item.year} value={item.year}>{item.year}</option>)}</select></div>
        <div className="min-w-0 space-y-1.5"><Label htmlFor="history-section">Section</Label><select id="history-section" className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={selectedSection} onChange={(event) => setSelectedSection(event.target.value)} disabled={!selectedYear}><option value="">All sections in this year</option>{uniqueSections.map((item) => <option key={item.section} value={item.section}>{item.section}</option>)}</select></div>
        <div className="min-w-0 space-y-1.5"><Label htmlFor="history-from">From Date</Label><Input id="history-from" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /></div>
        <div className="min-w-0 space-y-1.5"><Label htmlFor="history-to">To Date</Label><Input id="history-to" type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} /></div>
        <div className="min-w-0 space-y-1.5"><Label htmlFor="history-branch">Branch (optional)</Label><Input id="history-branch" value={branch} onChange={(event) => setBranch(event.target.value)} placeholder="All branches" /></div>
        <div className="min-w-0 space-y-1.5"><Label htmlFor="history-roll">Student roll number (optional)</Label><Input id="history-roll" value={rollNumber} onChange={(event) => setRollNumber(event.target.value)} placeholder="All students in scope" /></div>
        <div className="min-w-0 space-y-1.5"><Label htmlFor="history-format">Format</Label><select id="history-format" className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={format} onChange={(event) => setFormat(event.target.value as "pdf" | "xlsx" | "csv")}><option value="pdf">PDF</option><option value="xlsx">Excel (.xlsx)</option><option value="csv">CSV (.csv)</option></select></div>
        <Button className="w-full" onClick={exportHistory} disabled={loading || !selectedYear}>{loading ? "Preparing…" : "Export History"}</Button>
      </CardContent>
    </Card>
  );
}
