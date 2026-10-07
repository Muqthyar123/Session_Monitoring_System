import { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Layers,
  Plus,
  Edit2,
  Trash2,
  CheckCircle2,
  XCircle,
  Users,
  Download,
  Search,
  RefreshCw,
  Filter,
} from "lucide-react";
import { AdminLayout } from "@/layouts/AdminLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
  getSections,
  createSection,
  updateSection,
  deleteSection,
  type Section,
} from "@/services/sectionService";
import { getDepartments, type Department } from "@/services/departmentService";
import { exportToExcel } from "@/utils/exportUtils";

export const Route = createFileRoute("/admin/sections")({
  component: ManageSectionsPage,
});

const ACADEMIC_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"];

function ManageSectionsPage() {
  const [sections, setSections] = useState<Section[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [selectedYear, setSelectedYear] = useState<string>("ALL");
  const [selectedBranch, setSelectedBranch] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSection, setEditingSection] = useState<Section | null>(null);
  const [formYear, setFormYear] = useState("2nd Year");
  const [formBranch, setFormBranch] = useState("CSE");
  const [formSectionName, setFormSectionName] = useState("");
  const [formActive, setFormActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [secData, deptData] = await Promise.all([
        getSections(selectedYear === "ALL" ? undefined : selectedYear, selectedBranch === "ALL" ? undefined : selectedBranch),
        getDepartments().catch(() => []),
      ]);
      setSections(secData);
      setDepartments(deptData);
    } catch (err: any) {
      toast.error(err.message || "Failed to load academic sections.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedYear, selectedBranch]);

  const handleOpenAdd = () => {
    setEditingSection(null);
    setFormYear("2nd Year");
    setFormBranch(departments.length > 0 ? departments[0].code : "CSE");
    setFormSectionName("");
    setFormActive(true);
    setDialogOpen(true);
  };

  const handleOpenEdit = (sec: Section) => {
    setEditingSection(sec);
    setFormYear(sec.year || "2nd Year");
    setFormBranch(sec.branch || sec.department || "CSE");
    setFormSectionName(sec.sectionName);
    setFormActive(sec.isActive);
    setDialogOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formSectionName.trim()) {
      toast.error("Section name is required.");
      return;
    }

    try {
      setSubmitting(true);
      if (editingSection) {
        await updateSection(editingSection.id, {
          year: formYear,
          branch: formBranch.toUpperCase(),
          sectionName: formSectionName.trim().toUpperCase(),
          isActive: formActive,
        });
        toast.success(`Section '${formSectionName}' updated successfully.`);
      } else {
        await createSection({
          year: formYear,
          branch: formBranch.toUpperCase(),
          sectionName: formSectionName.trim().toUpperCase(),
          isActive: formActive,
        });
        toast.success(`Section '${formSectionName}' created successfully.`);
      }
      setDialogOpen(false);
      await loadData();
    } catch (err: any) {
      toast.error(err.message || "Failed to save section.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (sec: Section) => {
    if (!confirm(`Are you sure you want to delete or deactivate Section '${sec.sectionName}' for ${sec.year} ${sec.branch}?`)) {
      return;
    }
    try {
      const res = await deleteSection(sec.id);
      toast.success(res.action === "DEACTIVATED" ? `Section '${sec.sectionName}' deactivated.` : `Section '${sec.sectionName}' deleted.`);
      await loadData();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete section.");
    }
  };

  const handleExport = () => {
    const exportData = filteredSections.map((s) => ({
      "Academic Year": s.year,
      "Branch / Department": s.branch || s.department,
      "Section Name": s.sectionName,
      "Assigned CR": s.crName || "Unassigned",
      "Assigned LR": s.lrName || "Unassigned",
      "Enrolled Students": s.studentCount,
      Status: s.isActive ? "Active" : "Inactive",
    }));
    exportToExcel(exportData, "Academic_Sections");
    toast.success("Sections list exported successfully.");
  };

  const filteredSections = sections.filter((s) => {
    const matchSearch =
      s.sectionName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.branch && s.branch.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (s.year && s.year.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchSearch;
  });

  const availableBranches = Array.from(
    new Set([
      ...departments.map((d) => d.code),
      ...sections.map((s) => s.branch || s.department || "CSE"),
      "CSE", "ECE", "IT", "AIDS", "AIML", "EEE", "MECH", "CIVIL"
    ])
  ).filter(Boolean);

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Layers className="size-6 text-primary" />
              Manage Academic Sections
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Configure and organize sections across academic years, branches, and student groups.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
              <RefreshCw className={`size-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport} className="bg-emerald-600/10 text-emerald-600 hover:bg-emerald-600/20 border-emerald-500/30">
              <Download className="size-4 mr-2" />
              Export
            </Button>
            <Button size="sm" onClick={handleOpenAdd}>
              <Plus className="size-4 mr-2" />
              Add Section
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 bg-card p-4 rounded-xl border shadow-sm">
          <div className="w-48">
            <Label className="text-xs text-muted-foreground mb-1 block">Academic Year</Label>
            <Select value={selectedYear} onValueChange={setSelectedYear}>
              <SelectTrigger>
                <SelectValue placeholder="All Years" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Years</SelectItem>
                {ACADEMIC_YEARS.map((y) => (
                  <SelectItem key={y} value={y}>{y}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="w-48">
            <Label className="text-xs text-muted-foreground mb-1 block">Branch / Program</Label>
            <Select value={selectedBranch} onValueChange={setSelectedBranch}>
              <SelectTrigger>
                <SelectValue placeholder="All Branches" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Branches</SelectItem>
                {availableBranches.map((b) => (
                  <SelectItem key={b} value={b}>{b}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[200px]">
            <Label className="text-xs text-muted-foreground mb-1 block">Search</Label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
              <Input
                placeholder="Search by section name, year, or branch..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
        </div>

        {/* Sections Table */}
        <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Year</TableHead>
                <TableHead>Branch / Dept</TableHead>
                <TableHead>Section Name</TableHead>
                <TableHead className="text-center">Enrolled Students</TableHead>
                <TableHead>Assigned CR / LR</TableHead>
                <TableHead className="text-center">Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    Loading sections...
                  </TableCell>
                </TableRow>
              ) : filteredSections.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No sections found for the selected filters.
                  </TableCell>
                </TableRow>
              ) : (
                filteredSections.map((sec) => (
                  <TableRow key={sec.id}>
                    <TableCell className="font-semibold">{sec.year}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-medium bg-muted">
                        {sec.branch || sec.department}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-bold text-primary">{sec.sectionName}</TableCell>
                    <TableCell className="text-center font-medium">
                      <span className="inline-flex items-center gap-1">
                        <Users className="size-3.5 text-muted-foreground" />
                        {sec.studentCount || 0}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs space-y-0.5">
                        {sec.crName && <div><span className="text-muted-foreground">CR:</span> {sec.crName}</div>}
                        {sec.lrName && <div><span className="text-muted-foreground">LR:</span> {sec.lrName}</div>}
                        {!sec.crName && !sec.lrName && <span className="text-muted-foreground">Unassigned</span>}
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      {sec.isActive ? (
                        <Badge variant="default" className="bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/25 border-emerald-500/30">
                          Active
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="bg-rose-500/15 text-rose-600 hover:bg-rose-500/25 border-rose-500/30">
                          Inactive
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right space-x-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleOpenEdit(sec)}
                        title="Edit Section"
                      >
                        <Edit2 className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(sec)}
                        title="Delete / Deactivate"
                        className="text-rose-600 hover:text-rose-700 hover:bg-rose-500/10"
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Add / Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>{editingSection ? "Edit Section" : "Add New Academic Section"}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label htmlFor="sec-year">Academic Year</Label>
                <Select value={formYear} onValueChange={setFormYear}>
                  <SelectTrigger id="sec-year">
                    <SelectValue placeholder="Select Academic Year" />
                  </SelectTrigger>
                  <SelectContent>
                    {ACADEMIC_YEARS.map((y) => (
                      <SelectItem key={y} value={y}>{y}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="sec-branch">Branch / Department</Label>
                <Select value={formBranch} onValueChange={setFormBranch}>
                  <SelectTrigger id="sec-branch">
                    <SelectValue placeholder="Select Branch" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableBranches.map((b) => (
                      <SelectItem key={b} value={b}>{b}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="sec-name">Section Name (e.g. A, B, C, CSE-A)</Label>
                <Input
                  id="sec-name"
                  placeholder="A"
                  value={formSectionName}
                  onChange={(e) => setFormSectionName(e.target.value.toUpperCase())}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="sec-status">Status</Label>
                <Select
                  value={formActive ? "active" : "inactive"}
                  onValueChange={(v) => setFormActive(v === "active")}
                >
                  <SelectTrigger id="sec-status">
                    <SelectValue placeholder="Select Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <DialogFooter className="pt-4">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Saving..." : editingSection ? "Update Section" : "Create Section"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
}
