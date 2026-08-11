import { useMemo, useState, type FormEvent } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Download, Plus, Search, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { AdminLayout } from "@/layouts/AdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { FileUpload } from "@/components/common/FileUpload";
import { DataTable, type Column } from "@/components/common/DataTable";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  createCRLRUser,
  deleteCRLRUser,
  downloadCRLRTemplate,
  getCRLRUsers,
  updateCRLRUser,
  uploadCRLRExcel,
} from "@/services/userService";
import { MOCK_SECTIONS, MOCK_YEARS, type CRLRUser } from "@/data/mock/mockData";

export const Route = createFileRoute("/admin/cr-lr")({
  head: () => ({
    meta: [
      { title: "CR/LR Management — Faculty Attendance Monitor" },
      { name: "description", content: "Create, edit and upload Class and Lateral Representative records for each section." },
      { property: "og:title", content: "CR/LR Management — Faculty Attendance Monitor" },
      { property: "og:description", content: "Manage CR and LR records manually or via Excel upload." },
    ],
  }),
  component: CRLRManagementPage,
});

const ALL = "all";

type FormState = Omit<CRLRUser, "id">;

const emptyForm: FormState = {
  name: "",
  rollNumber: "",
  email: "",
  role: "CR",
  year: MOCK_YEARS[0]!,
  section: MOCK_SECTIONS[0]!,
};

function CRLRManagementPage() {
  const { data, loading, error, reload } = useAsyncData(() => getCRLRUsers(), []);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState(ALL);
  const [yearFilter, setYearFilter] = useState(ALL);
  const [sectionFilter, setSectionFilter] = useState(ALL);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<CRLRUser | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [saving, setSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<CRLRUser | null>(null);

  const rows = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (data ?? []).filter((u) => {
      const matchesTerm =
        !term ||
        u.name.toLowerCase().includes(term) ||
        u.rollNumber.toLowerCase().includes(term) ||
        u.email.toLowerCase().includes(term);
      return (
        matchesTerm &&
        (roleFilter === ALL || u.role === roleFilter) &&
        (yearFilter === ALL || u.year === yearFilter) &&
        (sectionFilter === ALL || u.section === sectionFilter)
      );
    });
  }, [data, search, roleFilter, yearFilter, sectionFilter]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setFormErrors({});
    setDialogOpen(true);
  };

  const openEdit = (user: CRLRUser) => {
    setEditing(user);
    const { id: _id, ...rest } = user;
    setForm(rest);
    setFormErrors({});
    setDialogOpen(true);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const errors: Partial<Record<keyof FormState, string>> = {};
    if (!form.name.trim()) errors.name = "Name is required.";
    if (!form.rollNumber.trim()) errors.rollNumber = "Roll number is required.";
    if (!form.email.trim()) errors.email = "Email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim()))
      errors.email = "Enter a valid email address.";
    setFormErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSaving(true);
    try {
      if (editing) {
        await updateCRLRUser(editing.id, form);
        toast.success("Record updated");
      } else {
        await createCRLRUser(form);
        toast.success("Record added");
      }
      setDialogOpen(false);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save the record.");
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    try {
      await deleteCRLRUser(pendingDelete.id);
      toast.success("Record deleted");
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not delete the record.");
    } finally {
      setPendingDelete(null);
    }
  };

  const columns: Column<CRLRUser>[] = [
    { key: "name", header: "Name", cell: (r) => r.name },
    { key: "roll", header: "Roll Number", cell: (r) => r.rollNumber },
    { key: "role", header: "Role", cell: (r) => r.role },
    { key: "year", header: "Year", cell: (r) => r.year },
    { key: "section", header: "Section", cell: (r) => r.section },
    { key: "email", header: "Email", cell: (r) => r.email },
    {
      key: "actions",
      header: "Actions",
      cell: (r) => (
        <div className="flex gap-1">
          <Button variant="ghost" size="icon" onClick={() => openEdit(r)} aria-label={`Edit ${r.name}`}>
            <Pencil className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setPendingDelete(r)}
            aria-label={`Delete ${r.name}`}
          >
            <Trash2 className="size-4 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <AdminLayout>
      <PageHeader
        title="CR/LR Management"
        description="Maintain the representatives responsible for reporting faculty attendance."
        actions={
          <>
            <Button variant="outline" onClick={downloadCRLRTemplate}>
              <Download className="size-4" /> Download CR/LR Template
            </Button>
            <Button onClick={openCreate}>
              <Plus className="size-4" /> Add Record
            </Button>
          </>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Upload CR/LR Excel</CardTitle>
          <CardDescription>
            Columns: Name, Roll Number, Email, Role, Year, Section. Validation happens in the backend.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FileUpload onUpload={uploadCRLRExcel} />
        </CardContent>
      </Card>

      <section className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name, roll number or email"
              className="pl-9"
              aria-label="Search records"
            />
          </div>
          <Select value={roleFilter} onValueChange={setRoleFilter}>
            <SelectTrigger aria-label="Filter by role">
              <SelectValue placeholder="Role" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All roles</SelectItem>
              <SelectItem value="CR">CR</SelectItem>
              <SelectItem value="LR">LR</SelectItem>
            </SelectContent>
          </Select>
          <Select value={yearFilter} onValueChange={setYearFilter}>
            <SelectTrigger aria-label="Filter by year">
              <SelectValue placeholder="Year" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All years</SelectItem>
              {MOCK_YEARS.map((y) => (
                <SelectItem key={y} value={y}>
                  {y}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={sectionFilter} onValueChange={setSectionFilter}>
            <SelectTrigger aria-label="Filter by section">
              <SelectValue placeholder="Section" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All sections</SelectItem>
              {MOCK_SECTIONS.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {loading ? (
          <LoadingState rows={5} />
        ) : error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No CR/LR records"
            description="No records match the current filters."
            action={
              <Button size="sm" onClick={openCreate}>
                Add Record
              </Button>
            }
          />
        ) : (
          <DataTable columns={columns} rows={rows} getRowId={(r) => r.id} />
        )}
      </section>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit CR/LR Record" : "Add CR/LR Record"}</DialogTitle>
            <DialogDescription>
              Only identification and communication details are stored.
            </DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
                {formErrors.name ? <p className="text-xs text-destructive">{formErrors.name}</p> : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="roll">Roll Number</Label>
                <Input
                  id="roll"
                  value={form.rollNumber}
                  onChange={(e) => setForm({ ...form, rollNumber: e.target.value })}
                />
                {formErrors.rollNumber ? (
                  <p className="text-xs text-destructive">{formErrors.rollNumber}</p>
                ) : null}
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
                {formErrors.email ? (
                  <p className="text-xs text-destructive">{formErrors.email}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label>Role</Label>
                <Select
                  value={form.role}
                  onValueChange={(value) => setForm({ ...form, role: value as "CR" | "LR" })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CR">CR</SelectItem>
                    <SelectItem value="LR">LR</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Year</Label>
                <Select value={form.year} onValueChange={(value) => setForm({ ...form, year: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MOCK_YEARS.map((y) => (
                      <SelectItem key={y} value={y}>
                        {y}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label>Section</Label>
                <Select
                  value={form.section}
                  onValueChange={(value) => setForm({ ...form, section: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MOCK_SECTIONS.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(pendingDelete)} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this record?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete?.name} ({pendingDelete?.rollNumber}) will be removed from the CR/LR list.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
