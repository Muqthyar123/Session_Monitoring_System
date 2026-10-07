import { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Building2,
  Plus,
  Edit2,
  Trash2,
  CheckCircle2,
  XCircle,
  Users,
  Layers,
  Download,
  Search,
  RefreshCw,
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
  getDepartments,
  createDepartment,
  updateDepartment,
  deleteDepartment,
  type Department,
} from "@/services/departmentService";
import { exportToExcel } from "@/utils/exportUtils";

export const Route = createFileRoute("/admin/departments")({
  component: ManageDepartmentsPage,
});

function ManageDepartmentsPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDept, setEditingDept] = useState<Department | null>(null);

  const [formCode, setFormCode] = useState("");
  const [formName, setFormName] = useState("");
  const [formActive, setFormActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await getDepartments();
      setDepartments(data);
    } catch (err: any) {
      toast.error(err.message || "Failed to load departments.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenAdd = () => {
    setEditingDept(null);
    setFormCode("");
    setFormName("");
    setFormActive(true);
    setDialogOpen(true);
  };

  const handleOpenEdit = (dept: Department) => {
    setEditingDept(dept);
    setFormCode(dept.code);
    setFormName(dept.name);
    setFormActive(dept.isActive);
    setDialogOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formCode.trim() || !formName.trim()) {
      toast.error("Department code and name are required.");
      return;
    }

    try {
      setSubmitting(true);
      if (editingDept) {
        await updateDepartment(editingDept.id, {
          code: formCode.trim().toUpperCase(),
          name: formName.trim(),
          isActive: formActive,
        });
        toast.success(`Department '${formCode}' updated successfully.`);
      } else {
        await createDepartment({
          code: formCode.trim().toUpperCase(),
          name: formName.trim(),
          isActive: formActive,
        });
        toast.success(`Department '${formCode}' created successfully.`);
      }
      setDialogOpen(false);
      await loadData();
    } catch (err: any) {
      toast.error(err.message || "Failed to save department.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (dept: Department) => {
    if (!confirm(`Are you sure you want to delete or deactivate department '${dept.code}'?`)) {
      return;
    }
    try {
      const res = await deleteDepartment(dept.id);
      toast.success(res.action === "DEACTIVATED" ? `Department '${dept.code}' deactivated.` : `Department '${dept.code}' deleted.`);
      await loadData();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete department.");
    }
  };

  const handleExport = () => {
    const exportData = filteredDepts.map((d) => ({
      "Department Code": d.code,
      "Department Name": d.name,
      Coordinator: d.coordinatorName || "Unassigned",
      "Total Students": d.studentCount,
      "Total Sections": d.sectionCount,
      "Total Faculty": d.facultyCount,
      Status: d.isActive ? "Active" : "Inactive",
    }));
    exportToExcel(exportData, "Academic_Departments");
    toast.success("Department list exported successfully.");
  };

  const filteredDepts = departments.filter(
    (d) =>
      d.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (d.coordinatorName && d.coordinatorName.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Building2 className="size-6 text-primary" />
              Manage Departments
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Configure academic branches, programs, and assign departmental coordinators.
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
              Add Department
            </Button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border bg-card p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
                <Building2 className="size-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">Total Departments</p>
                <p className="text-2xl font-bold">{departments.length}</p>
              </div>
            </div>
          </div>
          <div className="rounded-xl border bg-card p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-emerald-500/10 p-2.5 text-emerald-600">
                <Users className="size-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">Total Enrolled Students</p>
                <p className="text-2xl font-bold">
                  {departments.reduce((acc, d) => acc + (d.studentCount || 0), 0)}
                </p>
              </div>
            </div>
          </div>
          <div className="rounded-xl border bg-card p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-blue-500/10 p-2.5 text-blue-600">
                <Layers className="size-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">Total Sections</p>
                <p className="text-2xl font-bold">
                  {departments.reduce((acc, d) => acc + (d.sectionCount || 0), 0)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
            <Input
              placeholder="Search departments..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        {/* Departments Table */}
        <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Department / Branch Name</TableHead>
                <TableHead>Coordinator</TableHead>
                <TableHead className="text-center">Students</TableHead>
                <TableHead className="text-center">Sections</TableHead>
                <TableHead className="text-center">Faculty</TableHead>
                <TableHead className="text-center">Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                    Loading departments...
                  </TableCell>
                </TableRow>
              ) : filteredDepts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                    No departments found.
                  </TableCell>
                </TableRow>
              ) : (
                filteredDepts.map((dept) => (
                  <TableRow key={dept.id}>
                    <TableCell className="font-semibold text-primary">{dept.code}</TableCell>
                    <TableCell className="font-medium">{dept.name}</TableCell>
                    <TableCell>
                      {dept.coordinatorName ? (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium bg-muted px-2 py-1 rounded">
                          <Users className="size-3 text-muted-foreground" />
                          {dept.coordinatorName}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">Unassigned</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center font-medium">{dept.studentCount || 0}</TableCell>
                    <TableCell className="text-center font-medium">{dept.sectionCount || 0}</TableCell>
                    <TableCell className="text-center font-medium">{dept.facultyCount || 0}</TableCell>
                    <TableCell className="text-center">
                      {dept.isActive ? (
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
                        onClick={() => handleOpenEdit(dept)}
                        title="Edit Department"
                      >
                        <Edit2 className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(dept)}
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

        {/* Add/Edit Modal */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>{editingDept ? "Edit Department" : "Add New Department"}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label htmlFor="dept-code">Department Code (e.g. CSE, ECE, MECH)</Label>
                <Input
                  id="dept-code"
                  placeholder="CSE"
                  value={formCode}
                  onChange={(e) => setFormCode(e.target.value.toUpperCase())}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="dept-name">Department Full Name</Label>
                <Input
                  id="dept-name"
                  placeholder="Computer Science & Engineering"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="dept-status">Status</Label>
                <Select
                  value={formActive ? "active" : "inactive"}
                  onValueChange={(v) => setFormActive(v === "active")}
                >
                  <SelectTrigger id="dept-status">
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
                  {submitting ? "Saving..." : editingDept ? "Update Department" : "Create Department"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
}
