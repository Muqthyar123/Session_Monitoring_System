import { useMemo, useState, type FormEvent } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Download, Plus, Search, Pencil, Trash2, KeyRound } from "lucide-react";
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
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  createMentor,
  deleteMentor,
  downloadMentorTemplate,
  getMentors,
  updateMentor,
  uploadMentorExcel,
  type MentorItem,
} from "@/services/mentorService";

export const Route = createFileRoute("/admin/mentors")({
  head: () => ({
    meta: [
      { title: "Mentor Management — Admin Portal" },
      { name: "description", content: "Manage mentors, add mentors manually, or bulk import via Excel." },
    ],
  }),
  component: AdminMentorsPage,
});

interface MentorFormState {
  name: string;
  mentorId: string;
  email: string;
  phone: string;
  designation: string;
  department: string;
  profile: string;
  password?: string;
}

const emptyForm: MentorFormState = {
  name: "",
  mentorId: "",
  email: "",
  phone: "",
  designation: "",
  department: "",
  profile: "",
  password: "",
};

function AdminMentorsPage() {
  const { data, loading, error, reload } = useAsyncData(() => getMentors(), []);
  const [search, setSearch] = useState("");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<MentorItem | null>(null);
  const [form, setForm] = useState<MentorFormState>(emptyForm);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof MentorFormState, string>>>({});
  const [saving, setSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<MentorItem | null>(null);
  const [uploading, setUploading] = useState(false);

  const rows = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!data) return [];
    if (!term) return data;
    return data.filter(
      (m) =>
        m.name.toLowerCase().includes(term) ||
        m.mentorId.toLowerCase().includes(term) ||
        m.email.toLowerCase().includes(term) ||
        (m.phone && m.phone.toLowerCase().includes(term)) ||
        (m.designation && m.designation.toLowerCase().includes(term)) ||
        (m.department && m.department.toLowerCase().includes(term)) ||
        (m.profile && m.profile.toLowerCase().includes(term))
    );
  }, [data, search]);

  const openCreateDialog = () => {
    setEditing(null);
    setForm(emptyForm);
    setFormErrors({});
    setDialogOpen(true);
  };

  const openEditDialog = (mentor: MentorItem) => {
    setEditing(mentor);
    setForm({
      name: mentor.name,
      mentorId: mentor.mentorId,
      email: mentor.email,
      phone: mentor.phone || "",
      designation: mentor.designation || "",
      department: mentor.department || "",
      profile: mentor.profile || "",
      password: "",
    });
    setFormErrors({});
    setDialogOpen(true);
  };

  const validate = (): boolean => {
    const errs: Partial<Record<keyof MentorFormState, string>> = {};
    if (!form.name.trim()) errs.name = "Name is required.";
    if (!form.mentorId.trim()) errs.mentorId = "Mentor / Employee ID is required.";
    if (!form.email.trim()) {
      errs.email = "Email is required.";
    } else if (!form.email.includes("@")) {
      errs.email = "Enter a valid email.";
    }
    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    try {
      if (editing) {
        await updateMentor(editing.id, {
          name: form.name.trim(),
          mentorId: form.mentorId.trim(),
          email: form.email.trim(),
          phone: form.phone.trim() || undefined,
          designation: form.designation.trim() || undefined,
          department: form.department.trim() || undefined,
          profile: form.profile.trim() || undefined,
          ...(form.password?.trim() ? { password: form.password.trim() } : {}),
        });
        toast.success(`Mentor "${form.name}" updated successfully.`);
      } else {
        await createMentor({
          name: form.name.trim(),
          mentorId: form.mentorId.trim(),
          email: form.email.trim(),
          phone: form.phone.trim() || undefined,
          designation: form.designation.trim() || undefined,
          department: form.department.trim() || undefined,
          profile: form.profile.trim() || undefined,
          password: form.password?.trim() || "mentor1234",
        });
        toast.success(`Mentor "${form.name}" added successfully.`);
      }
      setDialogOpen(false);
      reload();
    } catch (err: any) {
      toast.error(err.message || "Failed to save mentor.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    try {
      await deleteMentor(pendingDelete.id);
      toast.success(`Mentor "${pendingDelete.name}" deleted.`);
      setPendingDelete(null);
      reload();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete mentor.");
    }
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      const result = await uploadMentorExcel(file);
      toast.success(result.message || "Mentors imported successfully!");
      reload();
    } catch (err: any) {
      toast.error(err.message || "Failed to upload Excel/CSV file.");
    } finally {
      setUploading(false);
    }
  };

  const columns: Column<MentorItem>[] = [
    {
      key: "mentorId",
      header: "Employee ID",
      cell: (r) => <span className="font-semibold text-primary">{r.mentorId}</span>,
    },
    { key: "name", header: "Full Name", cell: (r) => r.name },
    { key: "email", header: "Email Address", cell: (r) => r.email },
    {
      key: "designation",
      header: "Designation",
      cell: (r) => r.designation || <span className="text-muted-foreground font-mono text-xs">N/A</span>,
    },
    {
      key: "department",
      header: "Department",
      cell: (r) => r.department || <span className="text-muted-foreground font-mono text-xs">N/A</span>,
    },
    {
      key: "phone",
      header: "Mobile No",
      cell: (r) => r.phone || <span className="text-muted-foreground font-mono text-xs">N/A</span>,
    },
    {
      key: "profile",
      header: "Profile",
      cell: (r) => r.profile ? <span className="text-xs font-medium px-2 py-0.5 rounded bg-muted text-foreground">{r.profile}</span> : <span className="text-muted-foreground font-mono text-xs">N/A</span>,
    },
    {
      key: "actions",
      header: "Actions",
      cell: (r) => (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => openEditDialog(r)}
            title="Edit Mentor"
          >
            <Pencil className="size-4 text-muted-foreground hover:text-foreground" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setPendingDelete(r)}
            title="Delete Mentor"
          >
            <Trash2 className="size-4 text-destructive hover:text-destructive/80" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <AdminLayout>
      <PageHeader
        title="Mentor Management"
        description="Add, edit, or bulk import mentors using standard format (Name, Employee ID, Email, Designation, Department, Mobile No, Profile)."
        actions={
          <Button onClick={openCreateDialog}>
            <Plus className="size-4 mr-2" /> Add Mentor
          </Button>
        }
      />

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Mentor Directory</CardTitle>
            <CardDescription>
              View and manage active mentors across all departments.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative max-w-sm">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by name, ID, email, designation..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>

            {loading ? (
              <LoadingState label="Loading mentors..." />
            ) : error ? (
              <ErrorState title="Failed to load mentors" description={error.message} retry={reload} />
            ) : rows.length === 0 ? (
              <EmptyState
                title="No mentors found"
                description={search ? "No mentor matches your search criteria." : "Get started by adding a mentor or uploading an Excel/CSV sheet."}
                action={
                  <Button onClick={openCreateDialog} variant="outline" size="sm">
                    <Plus className="size-4 mr-2" /> Add First Mentor
                  </Button>
                }
              />
            ) : (
              <DataTable columns={columns} rows={rows} getRowId={(r) => r.id} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Bulk Excel / CSV Import</CardTitle>
            <CardDescription>
              Upload an `.xlsx`, `.xls`, or `.csv` file with attributes: Name, Employee ID, Email, Designation, Department, Mobile No, Profile.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={downloadMentorTemplate}
            >
              <Download className="size-4 mr-2" /> Download Template
            </Button>

            <FileUpload
              accept=".xlsx,.xls,.csv"
              onFileSelect={handleFileUpload}
              uploading={uploading}
              label="Click to browse or drop mentor Excel/CSV file"
            />
          </CardContent>
        </Card>
      </div>

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit Mentor" : "Add New Mentor"}</DialogTitle>
            <DialogDescription>
              {editing ? "Update the details for this mentor." : "Enter mentor details to create a new login account."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="mentorId">Employee ID / ID *</Label>
                <Input
                  id="mentorId"
                  placeholder="e.g. 605101"
                  value={form.mentorId}
                  onChange={(e) => setForm({ ...form, mentorId: e.target.value })}
                />
                {formErrors.mentorId && (
                  <p className="text-xs font-medium text-destructive">{formErrors.mentorId}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="name">Full Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g. SIVA NAGESWARA RAO"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
                {formErrors.name && (
                  <p className="text-xs font-medium text-destructive">{formErrors.name}</p>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="email">Email Address *</Label>
              <Input
                id="email"
                type="email"
                placeholder="drssnr@nrtec.in"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
              {formErrors.email && (
                <p className="text-xs font-medium text-destructive">{formErrors.email}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="designation">Designation</Label>
                <Input
                  id="designation"
                  placeholder="e.g. PROFESSOR"
                  value={form.designation}
                  onChange={(e) => setForm({ ...form, designation: e.target.value })}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="department">Department / Branch</Label>
                <Input
                  id="department"
                  placeholder="e.g. CSE"
                  value={form.department}
                  onChange={(e) => setForm({ ...form, department: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="phone">Mobile Number</Label>
                <Input
                  id="phone"
                  placeholder="e.g. 8977987777"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="profile">Profile / Roles</Label>
                <Input
                  id="profile"
                  placeholder="e.g. Faculty, Administrator"
                  value={form.profile}
                  onChange={(e) => setForm({ ...form, profile: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">
                {editing ? "New Password (leave blank to keep current)" : "Password (default: mentor1234)"}
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : editing ? "Update Mentor" : "Create Mentor"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!pendingDelete} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete mentor account <strong>{pendingDelete?.name}</strong> ({pendingDelete?.mentorId}). This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete Mentor
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
