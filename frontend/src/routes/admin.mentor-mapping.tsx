import { useState, useEffect, useRef } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Upload,
  Download,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Trash2,
  Users,
  Search,
  RefreshCw,
  FileSpreadsheet,
  Check,
  ShieldAlert,
  Info,
} from "lucide-react";
import { AdminLayout } from "@/layouts/AdminLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  downloadMappingTemplate,
  previewMentorMappings,
  confirmMentorMappings,
  getMentorMappings,
  deleteMentorMapping,
  type MentorMappingPreviewData,
  type MentorMappingRecord,
} from "@/services/mentorMappingService";

export const Route = createFileRoute("/admin/mentor-mapping")({
  component: AdminMentorMappingPage,
});

function AdminMentorMappingPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mappings, setMappings] = useState<MentorMappingRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [confirming, setConfirming] = useState(false);

  // Filters for current mappings list
  const [filterYear, setFilterYear] = useState<string>("ALL");
  const [filterSection, setFilterSection] = useState<string>("ALL");
  const [searchMentor, setSearchMentor] = useState<string>("");

  // Preview state
  const [previewData, setPreviewData] = useState<MentorMappingPreviewData | null>(null);
  const [importMode, setImportMode] = useState<"ADD_UPDATE" | "REPLACE">("ADD_UPDATE");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Delete modal state
  const [deleteTarget, setDeleteTarget] = useState<MentorMappingRecord | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchMappings = async () => {
    try {
      setLoading(true);
      const data = await getMentorMappings();
      setMappings(data);
    } catch (err: any) {
      toast.error(err.message || "An error occurred while fetching mentor mappings.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMappings();
  }, []);

  const handleDownloadTemplate = async () => {
    try {
      await downloadMappingTemplate();
      toast.success("Mentor_Student_Mapping_Template.xlsx downloaded successfully.");
    } catch (err: any) {
      toast.error(err.message || "Could not download Excel template.");
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".xlsx") && !file.name.endsWith(".xls")) {
      toast.error("Please select a valid Excel file (.xlsx or .xls).");
      return;
    }

    try {
      setUploading(true);
      setSelectedFile(file);
      const preview = await previewMentorMappings(file);
      setPreviewData(preview);
      toast.success(`Parsed ${preview.totalRows} row(s): ${preview.validRows} valid, ${preview.invalidRows} invalid.`);
    } catch (err: any) {
      toast.error(err.message || "Failed to parse Excel file.");
      setPreviewData(null);
      setSelectedFile(null);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleConfirmImport = async () => {
    if (!previewData || previewData.validRows === 0) return;

    try {
      setConfirming(true);
      const res = await confirmMentorMappings({
        mode: importMode,
        rows: previewData.rows,
      });

      toast.success(res.message || `${res.total_students_assigned} students mapped to their mentors.`);
      setPreviewData(null);
      setSelectedFile(null);
      await fetchMappings();
    } catch (err: any) {
      toast.error(err.message || "Failed to commit mentor mappings.");
    } finally {
      setConfirming(false);
    }
  };

  const handleDeleteMapping = async () => {
    if (!deleteTarget) return;
    try {
      setDeleting(true);
      await deleteMentorMapping(deleteTarget.id);
      toast.success(`Removed assignment for ${deleteTarget.mentorName} (${deleteTarget.year} - ${deleteTarget.section}).`);
      setDeleteTarget(null);
      await fetchMappings();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete mapping.");
    } finally {
      setDeleting(false);
    }
  };

  // Filtered current mappings
  const distinctYears = Array.from(new Set(mappings.map((m) => m.year))).filter(Boolean);
  const distinctSections = Array.from(new Set(mappings.map((m) => m.section))).filter(Boolean);

  const filteredMappings = mappings.filter((m) => {
    if (filterYear !== "ALL" && m.year !== filterYear) return false;
    if (filterSection !== "ALL" && m.section !== filterSection) return false;
    if (
      searchMentor.trim() &&
      !m.mentorName.toLowerCase().includes(searchMentor.trim().toLowerCase()) &&
      !m.mentorEmail?.toLowerCase().includes(searchMentor.trim().toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const totalAssignedStudents = mappings.reduce((acc, m) => acc + (m.studentCount || 0), 0);

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6 p-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Users className="size-6 text-primary" />
              Mentor-to-Student Mapping
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Bulk map faculty mentors to academic sections or specific student roll-number serial ranges using Excel.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={handleDownloadTemplate}
              className="gap-2 border-primary/30 hover:border-primary text-primary"
            >
              <Download className="size-4" />
              Download Excel Template
            </Button>
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="gap-2 shadow-sm"
            >
              <Upload className="size-4" />
              {uploading ? "Analyzing File..." : "Upload Mapping File"}
            </Button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".xlsx,.xls"
              className="hidden"
            />
          </div>
        </div>

        {/* Excel Import & Validation Preview Panel */}
        {previewData && (
          <Card className="border-primary/40 bg-card shadow-md animate-in fade-in duration-200">
            <CardHeader className="pb-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-lg font-semibold flex items-center gap-2 text-primary">
                    <FileSpreadsheet className="size-5 text-primary" />
                    Mapping Import Preview & Validation Report
                  </CardTitle>
                  <CardDescription className="mt-1">
                    File: <span className="font-medium text-foreground">{selectedFile?.name}</span> • Please review the validation status before applying changes to MongoDB.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setPreviewData(null);
                      setSelectedFile(null);
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleConfirmImport}
                    disabled={confirming || previewData.validRows === 0}
                    className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    {confirming ? (
                      <RefreshCw className="size-4 animate-spin" />
                    ) : (
                      <Check className="size-4" />
                    )}
                    Confirm & Apply ({previewData.validRows} Valid Rows)
                  </Button>
                </div>
              </div>

              {/* Metrics bar */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-4">
                <div className="rounded-lg border bg-muted/40 p-3 text-center">
                  <p className="text-xs text-muted-foreground font-medium">Total Rows</p>
                  <p className="text-xl font-bold text-foreground mt-0.5">{previewData.totalRows}</p>
                </div>
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/30 p-3 text-center">
                  <p className="text-xs text-emerald-800 dark:text-emerald-300 font-medium">Valid Rows</p>
                  <p className="text-xl font-bold text-emerald-700 dark:text-emerald-400 mt-0.5">{previewData.validRows}</p>
                </div>
                <div className="rounded-lg border border-rose-200 bg-rose-50 dark:bg-rose-950/30 p-3 text-center">
                  <p className="text-xs text-rose-800 dark:text-rose-300 font-medium">Invalid Rows</p>
                  <p className="text-xl font-bold text-rose-700 dark:text-rose-400 mt-0.5">{previewData.invalidRows}</p>
                </div>
                <div className="rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-950/30 p-3 text-center">
                  <p className="text-xs text-blue-800 dark:text-blue-300 font-medium">Students to Assign</p>
                  <p className="text-xl font-bold text-blue-700 dark:text-blue-400 mt-0.5">{previewData.studentsToAssign}</p>
                </div>
                <div className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/30 p-3 text-center">
                  <p className="text-xs text-amber-800 dark:text-amber-300 font-medium">Conflicts Detected</p>
                  <p className="text-xl font-bold text-amber-700 dark:text-amber-400 mt-0.5">{previewData.conflictsCount}</p>
                </div>
              </div>

              {/* Import Mode Selector */}
              <div className="flex items-center gap-4 mt-4 bg-muted/30 p-3 rounded-lg border text-sm">
                <span className="font-medium text-foreground">Import Mode:</span>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="importMode"
                    value="ADD_UPDATE"
                    checked={importMode === "ADD_UPDATE"}
                    onChange={() => setImportMode("ADD_UPDATE")}
                    className="accent-primary"
                  />
                  <span>Safe Merge (Add / Update Mappings)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-destructive">
                  <input
                    type="radio"
                    name="importMode"
                    value="REPLACE"
                    checked={importMode === "REPLACE"}
                    onChange={() => setImportMode("REPLACE")}
                    className="accent-destructive"
                  />
                  <span>Replace All Existing Mappings</span>
                </label>
              </div>
            </CardHeader>

            <CardContent>
              <div className="rounded-md border overflow-x-auto max-h-80">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="w-12 text-center">#</TableHead>
                      <TableHead>Mentor Name</TableHead>
                      <TableHead>Year</TableHead>
                      <TableHead>Section</TableHead>
                      <TableHead>Serial Range</TableHead>
                      <TableHead className="text-center">Matched Students</TableHead>
                      <TableHead>Status / Diagnostic</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {previewData.rows.map((r, idx) => (
                      <TableRow key={idx} className={r.status === "ERROR" ? "bg-rose-50/50 dark:bg-rose-950/20" : ""}>
                        <TableCell className="text-center text-xs text-muted-foreground">{r.rowIdx}</TableCell>
                        <TableCell className="font-medium">{r.mentorName}</TableCell>
                        <TableCell>{r.year}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{r.section}</Badge>
                        </TableCell>
                        <TableCell>
                          {r.isFullSection ? (
                            <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                              Entire Section (All)
                            </Badge>
                          ) : (
                            <span className="font-mono text-xs">
                              S.No {r.startSerial} - {r.endSerial}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-center font-semibold">
                          {r.studentCount}
                        </TableCell>
                        <TableCell>
                          {r.status === "VALID" ? (
                            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                              <CheckCircle2 className="size-4" />
                              Valid
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-rose-700 dark:text-rose-400">
                              <XCircle className="size-4 shrink-0" />
                              {r.errorMessage || "Validation failed"}
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Existing Mappings Overview */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <Users className="size-5 text-primary" />
                  Active Mentor-to-Student Mappings ({filteredMappings.length})
                </CardTitle>
                <CardDescription>
                  Total students assigned across all active mentor mappings: <span className="font-semibold text-foreground">{totalAssignedStudents}</span>
                </CardDescription>
              </div>

              {/* Filters */}
              <div className="flex flex-wrap items-center gap-2.5">
                <div className="relative w-48">
                  <Search className="size-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search mentor..."
                    value={searchMentor}
                    onChange={(e) => setSearchMentor(e.target.value)}
                    className="pl-8 h-9 text-xs"
                  />
                </div>

                <Select value={filterYear} onValueChange={setFilterYear}>
                  <SelectTrigger className="w-36 h-9 text-xs">
                    <SelectValue placeholder="All Years" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Years</SelectItem>
                    {distinctYears.map((y) => (
                      <SelectItem key={y} value={y}>
                        {y}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={filterSection} onValueChange={setFilterSection}>
                  <SelectTrigger className="w-36 h-9 text-xs">
                    <SelectValue placeholder="All Sections" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Sections</SelectItem>
                    {distinctSections.map((s) => (
                      <SelectItem key={s} value={s}>
                        Section {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchMappings}
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
                <p className="text-sm">Loading mentor assignments...</p>
              </div>
            ) : filteredMappings.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground border rounded-lg border-dashed flex flex-col items-center gap-2">
                <Users className="size-8 text-muted-foreground/50" />
                <p className="text-sm font-medium">No mentor mappings found.</p>
                <p className="text-xs text-muted-foreground max-w-sm">
                  Upload an Excel file using the template above to assign mentors to sections or roll-number ranges.
                </p>
              </div>
            ) : (
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Mentor Name</TableHead>
                      <TableHead>Email / ID</TableHead>
                      <TableHead>Academic Year</TableHead>
                      <TableHead>Section</TableHead>
                      <TableHead>Assigned Range</TableHead>
                      <TableHead className="text-center">Assigned Students</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredMappings.map((m) => (
                      <TableRow key={m.id}>
                        <TableCell className="font-semibold text-foreground">
                          {m.mentorName}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {m.mentorEmail || m.mentorId}
                        </TableCell>
                        <TableCell>{m.year}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="font-medium">
                            {m.section}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {m.isFullSection ? (
                            <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 text-xs">
                              Full Section
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="font-mono text-xs">
                              S.No {m.startSerial ?? 1} - {m.endSerial}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary">
                            {m.studentCount} students
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setDeleteTarget(m)}
                            className="text-destructive hover:bg-destructive/10 h-8 w-8 p-0"
                            title="Remove mapping"
                          >
                            <Trash2 className="size-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Delete Confirmation Dialog */}
        <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-destructive">
                <ShieldAlert className="size-5" />
                Remove Mentor Mapping
              </DialogTitle>
              <DialogDescription className="pt-2">
                Are you sure you want to remove the mapping for{" "}
                <span className="font-semibold text-foreground">{deleteTarget?.mentorName}</span> in{" "}
                <span className="font-semibold text-foreground">
                  {deleteTarget?.year} Section {deleteTarget?.section}
                </span>
                ?
                <br />
                <br />
                This will unassign the <span className="font-semibold">{deleteTarget?.studentCount}</span> student(s) from this mentor.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter className="mt-4 gap-2">
              <Button
                variant="outline"
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteMapping}
                disabled={deleting}
                className="gap-2"
              >
                {deleting ? <RefreshCw className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
                Confirm Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
}
