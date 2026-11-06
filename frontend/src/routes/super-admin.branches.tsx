import { useState, useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  GitBranch,
  Plus,
  Search,
  Edit2,
  Trash2,
  Building2,
  UserCheck,
  AlertTriangle,
  Loader2,
  AlertCircle,
  Filter,
} from "lucide-react";
import { toast } from "sonner";
import { SuperAdminLayout } from "@/layouts/SuperAdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState, ErrorState, EmptyState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { Card, CardContent } from "@/components/ui/card";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  getBranches,
  createBranch,
  updateBranch,
  deleteBranch,
  getSites,
} from "@/services/superAdminService";
import type { Branch } from "@/data/mock/mockData";

export const Route = createFileRoute("/super-admin/branches")({
  head: () => ({
    meta: [
      { title: "Branches Management — Super Admin" },
      { name: "description", content: "Create, configure, and manage academic branches and departments across campuses." },
    ],
  }),
  component: SuperAdminBranchesPage,
});

function SuperAdminBranchesPage() {
  const { data: branches, loading, error, reload } = useAsyncData(() => getBranches(), []);
  const { data: sites } = useAsyncData(() => getSites(), []);

  const [searchTerm, setSearchTerm] = useState("");
  const [selectedSiteFilter, setSelectedSiteFilter] = useState<string>("ALL");

  // Create / Edit modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingBranch, setEditingBranch] = useState<Branch | null>(null);
  const [formData, setFormData] = useState({
    code: "",
    name: "",
    siteId: "",
    description: "",
    isActive: true,
  });
  const [saving, setSaving] = useState(false);

  // Delete modal state
  const [deleteTarget, setDeleteTarget] = useState<Branch | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Filtered branches
  const filteredBranches = useMemo(() => {
    return (branches || []).filter((b) => {
      const q = searchTerm.toLowerCase();
      const matchesSearch =
        b.name.toLowerCase().includes(q) ||
        b.code.toLowerCase().includes(q) ||
        (b.hodName && b.hodName.toLowerCase().includes(q));
      const matchesSite =
        selectedSiteFilter === "ALL" || b.siteId === selectedSiteFilter;
      return matchesSearch && matchesSite;
    });
  }, [branches, searchTerm, selectedSiteFilter]);

  const handleOpenCreate = () => {
    setEditingBranch(null);
    setFormData({
      code: "",
      name: "",
      siteId: sites && sites.length > 0 ? (sites[0]?.id ?? "") : "",
      description: "",
      isActive: true,
    });
    setModalOpen(true);
  };

  const handleOpenEdit = (branch: Branch) => {
    setEditingBranch(branch);
    setFormData({
      code: branch.code,
      name: branch.name,
      siteId: branch.siteId || (sites && sites.length > 0 ? (sites[0]?.id ?? "") : ""),
      description: branch.description || "",
      isActive: branch.isActive,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.code.trim() || !formData.name.trim()) {
      toast.error("Branch Code and Name are required");
      return;
    }

    setSaving(true);
    try {
      const selectedSite = sites?.find((s) => s.id === formData.siteId);
      if (editingBranch) {
        await updateBranch(editingBranch.id, {
          name: formData.name,
          siteId: formData.siteId || undefined,
          siteName: selectedSite?.name ?? undefined,
          siteCode: selectedSite?.code ?? undefined,
          description: formData.description || undefined,
          isActive: formData.isActive,
        });
        toast.success(`Branch "${formData.name}" updated successfully`);
      } else {
        await createBranch({
          code: formData.code.toUpperCase(),
          name: formData.name,
          siteId: formData.siteId || undefined,
          siteName: selectedSite?.name ?? undefined,
          siteCode: selectedSite?.code ?? undefined,
          description: formData.description || undefined,
          isActive: formData.isActive,
        });
        toast.success(`Branch "${formData.name}" created successfully`);
      }
      setModalOpen(false);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save branch");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteBranch(deleteTarget.id);
      toast.success(`Branch "${deleteTarget.name}" deleted successfully`);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete branch");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <PageHeader
            title="Branches Management"
            description="Manage academic engineering branches, departments, and their administrative associations"
          />
          <Button
            onClick={handleOpenCreate}
            className="gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs cursor-pointer"
          >
            <Plus className="size-3.5" /> Add New Branch
          </Button>
        </div>

        {/* Filter Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
            <Input
              placeholder="Search by branch code, name, or HOD..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 text-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="size-4 text-muted-foreground shrink-0" />
            <Select value={selectedSiteFilter} onValueChange={setSelectedSiteFilter}>
              <SelectTrigger className="w-[180px] text-xs">
                <SelectValue placeholder="Filter by Campus" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">
                  All Campuses
                </SelectItem>
                {(sites || []).map((s) => (
                  <SelectItem key={s.id} value={s.id} className="text-xs">
                    {s.name} ({s.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Content */}
        {loading && !branches && <LoadingState label="Loading branches..." />}
        {error && !branches && <ErrorState message={error ?? undefined} onRetry={reload} />}

        {branches && (
          <Card className="border-border">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-border bg-muted/40 text-muted-foreground uppercase tracking-wider text-[11px] font-semibold">
                      <th className="py-3 px-4">Code</th>
                      <th className="py-3 px-4">Branch Name</th>
                      <th className="py-3 px-4">Campus / Site</th>
                      <th className="py-3 px-4">Assigned HOD</th>
                      <th className="py-3 px-4 text-center">Mentors</th>
                      <th className="py-3 px-4 text-center">Students</th>
                      <th className="py-3 px-4 text-center">Sections</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredBranches.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="py-10 text-center">
                          <EmptyState
                            title="No branches found"
                            description={
                              searchTerm || selectedSiteFilter !== "ALL"
                                ? "No branches match your current filter criteria."
                                : "No branches configured yet. Click 'Add New Branch' to begin."
                            }
                            action={
                              !searchTerm && selectedSiteFilter === "ALL" ? (
                                <Button onClick={handleOpenCreate} size="sm" className="mt-2 text-xs">
                                  Add New Branch
                                </Button>
                              ) : undefined
                            }
                          />
                        </td>
                      </tr>
                    ) : (
                      filteredBranches.map((branch) => (
                        <tr key={branch.id} className="hover:bg-muted/20 transition-colors">
                          <td className="py-3.5 px-4 font-mono font-bold text-indigo-600">
                            <Badge variant="outline" className="border-indigo-200 bg-indigo-50/50 font-mono">
                              {branch.code}
                            </Badge>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-foreground">{branch.name}</div>
                            {branch.description && (
                              <div className="text-[11px] text-muted-foreground line-clamp-1">
                                {branch.description}
                              </div>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-muted-foreground">
                            <div className="flex items-center gap-1.5">
                              <Building2 className="size-3.5 text-muted-foreground" />
                              <span>{branch.siteName || "Main Campus"}</span>
                            </div>
                          </td>
                          <td className="py-3.5 px-4">
                            {branch.hodName ? (
                              <div className="space-y-0.5">
                                <div className="font-medium text-foreground flex items-center gap-1.5">
                                  <UserCheck className="size-3.5 text-emerald-600" />
                                  <span>{branch.hodName}</span>
                                </div>
                                <div className="text-[11px] text-muted-foreground">{branch.hodEmail}</div>
                              </div>
                            ) : (
                              <Badge variant="secondary" className="bg-amber-50 text-amber-800 border-amber-200 text-[10px] gap-1">
                                <AlertCircle className="size-3" /> Unassigned
                              </Badge>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-center font-medium text-indigo-600">
                            {branch.mentorCount ?? branch.mentorsCount ?? 0}
                          </td>
                          <td className="py-3.5 px-4 text-center font-bold text-emerald-600">
                            {branch.studentCount ?? branch.studentsCount ?? 0}
                          </td>
                          <td className="py-3.5 px-4 text-center font-medium">
                            {branch.sectionCount ?? branch.sectionsCount ?? 0}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            {branch.isActive ? (
                              <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-0 text-[10px]">
                                Active
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="text-[10px]">
                                Inactive
                              </Badge>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenEdit(branch)}
                                className="size-8 p-0 text-muted-foreground hover:text-foreground cursor-pointer"
                                title="Edit Branch"
                              >
                                <Edit2 className="size-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setDeleteTarget(branch)}
                                className="size-8 p-0 text-rose-500 hover:text-rose-700 hover:bg-rose-50 cursor-pointer"
                                title="Delete Branch"
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Create / Edit Dialog */}
        <Dialog open={modalOpen} onOpenChange={setModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-bold">
                {editingBranch ? "Edit Branch" : "Add New Academic Branch"}
              </DialogTitle>
              <DialogDescription className="text-xs">
                Configure department code, campus affiliation, and branch details.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-3.5 pt-2">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="branch-code" className="text-xs font-semibold">
                    Branch Code *
                  </Label>
                  <Input
                    id="branch-code"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    placeholder="e.g. CSE"
                    disabled={Boolean(editingBranch)}
                    className="text-xs font-mono uppercase"
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="branch-site" className="text-xs font-semibold">
                    Campus / Site *
                  </Label>
                  <Select
                    value={formData.siteId}
                    onValueChange={(val) => setFormData({ ...formData, siteId: val })}
                  >
                    <SelectTrigger id="branch-site" className="text-xs">
                      <SelectValue placeholder="Select Campus" />
                    </SelectTrigger>
                    <SelectContent>
                      {(sites || []).map((s) => (
                        <SelectItem key={s.id} value={s.id} className="text-xs">
                          {s.name} ({s.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="branch-name" className="text-xs font-semibold">
                  Branch Name *
                </Label>
                <Input
                  id="branch-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Computer Science and Engineering"
                  className="text-xs"
                  required
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="branch-desc" className="text-xs font-semibold">
                  Description
                </Label>
                <Textarea
                  id="branch-desc"
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Department curriculum, specialization, notes..."
                  className="text-xs"
                />
              </div>

              <DialogFooter className="pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setModalOpen(false)}
                  disabled={saving}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={saving}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs gap-1.5"
                >
                  {saving && <Loader2 className="size-3.5 animate-spin" />}
                  {editingBranch ? "Save Changes" : "Create Branch"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Alert Dialog */}
        <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle className="flex items-center gap-2 text-rose-600 text-base">
                <AlertTriangle className="size-5" /> Delete Academic Branch?
              </AlertDialogTitle>
              <AlertDialogDescription className="text-xs space-y-2">
                <p>
                  Are you sure you want to delete branch <strong>{deleteTarget?.name}</strong> ({deleteTarget?.code})?
                </p>
                {deleteTarget &&
                  (((deleteTarget.studentCount ?? deleteTarget.studentsCount ?? 0) > 0) ||
                    ((deleteTarget.mentorCount ?? deleteTarget.mentorsCount ?? 0) > 0) ||
                    ((deleteTarget.sectionCount ?? deleteTarget.sectionsCount ?? 0) > 0) ||
                    Boolean(deleteTarget.hodName)) && (
                    <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded text-rose-800 dark:text-rose-300 font-medium text-xs space-y-1">
                      <div className="font-bold">Accidental Data Loss Prevention Alert:</div>
                      <div>
                        This branch currently has:
                        <ul className="list-disc pl-4 mt-1 space-y-0.5">
                          {deleteTarget.hodName && <li>Assigned HOD: {deleteTarget.hodName}</li>}
                          {((deleteTarget.studentCount ?? deleteTarget.studentsCount ?? 0) > 0) && (
                            <li>{deleteTarget.studentCount ?? deleteTarget.studentsCount} Students</li>
                          )}
                          {((deleteTarget.mentorCount ?? deleteTarget.mentorsCount ?? 0) > 0) && (
                            <li>{deleteTarget.mentorCount ?? deleteTarget.mentorsCount} Mentors</li>
                          )}
                          {((deleteTarget.sectionCount ?? deleteTarget.sectionsCount ?? 0) > 0) && (
                            <li>{deleteTarget.sectionCount ?? deleteTarget.sectionsCount} Sections</li>
                          )}
                        </ul>
                      </div>
                      <div className="text-[11px] text-rose-600 dark:text-rose-400 mt-1">
                        Please reassign or delete these records before removing this branch.
                      </div>
                    </div>
                  )}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={deleting} className="text-xs">
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                disabled={deleting}
                className="bg-rose-600 hover:bg-rose-700 text-white text-xs gap-1.5"
              >
                {deleting && <Loader2 className="size-3.5 animate-spin" />}
                Confirm Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </SuperAdminLayout>
  );
}
