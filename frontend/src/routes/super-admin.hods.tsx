import { useState, useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  KeyRound,
  ShieldCheck,
  Mail,
  Phone,
  AlertTriangle,
  Loader2,
  Eye,
  EyeOff,
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
  getHods,
  createHod,
  updateHod,
  resetHodPassword,
  toggleHodStatus,
  deleteHod,
  getBranches,
} from "@/services/superAdminService";
import type { HODItem } from "@/data/mock/mockData";

export const Route = createFileRoute("/super-admin/hods")({
  head: () => ({
    meta: [
      { title: "HOD Management — Super Admin" },
      { name: "description", content: "Create and govern Branch Head of Department (HOD) accounts and credentials." },
    ],
  }),
  component: SuperAdminHodsPage,
});

function SuperAdminHodsPage() {
  const { data: hods, loading, error, reload } = useAsyncData(() => getHods(), []);
  const { data: branches } = useAsyncData(() => getBranches(), []);

  const [searchTerm, setSearchTerm] = useState("");
  const [selectedBranchFilter, setSelectedBranchFilter] = useState<string>("ALL");

  // Create Modal state
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createFormData, setCreateFormData] = useState({
    name: "",
    email: "",
    phone: "",
    branchCode: "",
    password: "",
  });
  const [showCreatePassword, setShowCreatePassword] = useState(false);
  const [creating, setCreating] = useState(false);

  // Edit Modal state
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingHod, setEditingHod] = useState<HODItem | null>(null);
  const [editFormData, setEditFormData] = useState({
    name: "",
    email: "",
    phone: "",
    branchCode: "",
    isActive: true,
  });
  const [savingEdit, setSavingEdit] = useState(false);

  // Reset Password Modal state
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [targetResetHod, setTargetResetHod] = useState<HODItem | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [resettingPassword, setResettingPassword] = useState(false);

  // Delete Dialog state
  const [deleteTarget, setDeleteTarget] = useState<HODItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Filtered HOD list
  const filteredHods = useMemo(() => {
    return (hods || []).filter((h) => {
      const q = searchTerm.toLowerCase();
      const matchesSearch =
        h.name.toLowerCase().includes(q) ||
        h.email.toLowerCase().includes(q) ||
        (h.branchCode && h.branchCode.toLowerCase().includes(q)) ||
        (h.branchName && h.branchName.toLowerCase().includes(q)) ||
        (h.employeeId && h.employeeId.toLowerCase().includes(q));
      const matchesBranch =
        selectedBranchFilter === "ALL" || h.branchCode === selectedBranchFilter;
      return matchesSearch && matchesBranch;
    });
  }, [hods, searchTerm, selectedBranchFilter]);

  // Open Create
  const handleOpenCreate = () => {
    const defaultBranch = branches && branches.length > 0 ? branches[0]?.code ?? "" : "";
    setCreateFormData({
      name: "",
      email: "",
      phone: "",
      branchCode: defaultBranch,
      password: "",
    });
    setShowCreatePassword(false);
    setCreateModalOpen(true);
  };

  // Submit Create
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createFormData.name.trim() || !createFormData.email.trim() || !createFormData.branchCode) {
      toast.error("Name, email, and branch are required");
      return;
    }
    if (!createFormData.password || createFormData.password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }

    setCreating(true);
    try {
      const matchedBranch = branches?.find((b) => b.code === createFormData.branchCode);
      await createHod({
        name: createFormData.name,
        email: createFormData.email,
        phone: createFormData.phone || undefined,
        branchCode: createFormData.branchCode,
        branchId: matchedBranch?.id || undefined,
        password: createFormData.password,
        isActive: true,
      });
      toast.success(`HOD account created for ${createFormData.name} (${createFormData.branchCode})`);
      setCreateModalOpen(false);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create HOD account");
    } finally {
      setCreating(false);
    }
  };

  // Open Edit
  const handleOpenEdit = (hod: HODItem) => {
    setEditingHod(hod);
    setEditFormData({
      name: hod.name,
      email: hod.email,
      phone: hod.phone || "",
      branchCode: hod.branchCode || "",
      isActive: hod.isActive,
    });
    setEditModalOpen(true);
  };

  // Submit Edit
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingHod) return;
    if (!editFormData.name.trim() || !editFormData.email.trim() || !editFormData.branchCode) {
      toast.error("Name, email, and branch are required");
      return;
    }

    setSavingEdit(true);
    try {
      const matchedBranch = branches?.find((b) => b.code === editFormData.branchCode);
      await updateHod(editingHod.id, {
        name: editFormData.name,
        email: editFormData.email,
        phone: editFormData.phone || undefined,
        branchCode: editFormData.branchCode,
        branchId: matchedBranch?.id || undefined,
        isActive: editFormData.isActive,
      });
      toast.success(`HOD "${editFormData.name}" updated successfully`);
      setEditModalOpen(false);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update HOD");
    } finally {
      setSavingEdit(false);
    }
  };

  // Open Reset Password
  const handleOpenResetPassword = (hod: HODItem) => {
    setTargetResetHod(hod);
    setNewPassword("");
    setShowNewPassword(false);
    setResetModalOpen(true);
  };

  // Submit Reset Password
  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetResetHod) return;
    if (!newPassword || newPassword.length < 6) {
      toast.error("New password must be at least 6 characters");
      return;
    }

    setResettingPassword(true);
    try {
      await resetHodPassword(targetResetHod.id, newPassword);
      toast.success(`Password reset successfully for ${targetResetHod.name}`);
      setResetModalOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to reset password");
    } finally {
      setResettingPassword(false);
    }
  };

  // Toggle Status
  const handleToggleStatus = async (hod: HODItem) => {
    try {
      await toggleHodStatus(hod.id);
      toast.success(`HOD ${hod.name} is now ${hod.isActive ? "Inactive" : "Active"}`);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to change status");
    }
  };

  // Delete HOD
  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteHod(deleteTarget.id);
      toast.success(`HOD ${deleteTarget.name} removed successfully`);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete HOD");
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
            title="HOD Management"
            description="Provision and administer Head of Department accounts with branch-isolated governance"
          />
          <Button
            onClick={handleOpenCreate}
            className="gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs cursor-pointer"
          >
            <Plus className="size-3.5" /> Create HOD Account
          </Button>
        </div>

        {/* Filter Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
            <Input
              placeholder="Search by HOD name, email, or branch..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 text-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="size-4 text-muted-foreground shrink-0" />
            <Select value={selectedBranchFilter} onValueChange={setSelectedBranchFilter}>
              <SelectTrigger className="w-[180px] text-xs">
                <SelectValue placeholder="Filter by Branch" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">
                  All Branches
                </SelectItem>
                {(branches || []).map((b) => (
                  <SelectItem key={b.code} value={b.code} className="text-xs">
                    {b.code} — {b.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Content */}
        {loading && !hods && <LoadingState label="Loading HOD records..." />}
        {error && !hods && <ErrorState message={error ?? undefined} onRetry={reload} />}

        {hods && (
          <Card className="border-border">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-border bg-muted/40 text-muted-foreground uppercase tracking-wider text-[11px] font-semibold">
                      <th className="py-3 px-4">HOD Name</th>
                      <th className="py-3 px-4">Email / Login ID</th>
                      <th className="py-3 px-4">Assigned Branch</th>
                      <th className="py-3 px-4">Phone</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredHods.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-10 text-center">
                          <EmptyState
                            title="No HOD accounts found"
                            description={
                              searchTerm || selectedBranchFilter !== "ALL"
                                ? "No HODs match your current filter criteria."
                                : "No branch HODs created yet. Click 'Create HOD Account' to add one."
                            }
                            action={
                              !searchTerm && selectedBranchFilter === "ALL" ? (
                                <Button onClick={handleOpenCreate} size="sm" className="mt-2 text-xs">
                                  Create HOD Account
                                </Button>
                              ) : undefined
                            }
                          />
                        </td>
                      </tr>
                    ) : (
                      filteredHods.map((hod) => (
                        <tr key={hod.id} className="hover:bg-muted/20 transition-colors">
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-foreground flex items-center gap-2">
                              <div className="flex size-7 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs">
                                <ShieldCheck className="size-4" />
                              </div>
                              <span>{hod.name}</span>
                            </div>
                            {hod.employeeId && (
                              <div className="text-[11px] text-muted-foreground ml-9">
                                ID: {hod.employeeId}
                              </div>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-1.5 text-foreground font-medium">
                              <Mail className="size-3 text-muted-foreground" />
                              <span>{hod.email}</span>
                            </div>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="font-mono text-indigo-600 border-indigo-200 bg-indigo-50/50">
                                {hod.branchCode || "—"}
                              </Badge>
                              {hod.branchName && (
                                <span className="text-muted-foreground text-xs truncate max-w-[160px]">
                                  {hod.branchName}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-3.5 px-4 text-muted-foreground">
                            {hod.phone ? (
                              <div className="flex items-center gap-1.5">
                                <Phone className="size-3 text-muted-foreground" />
                                <span>{hod.phone}</span>
                              </div>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            <button
                              type="button"
                              onClick={() => handleToggleStatus(hod)}
                              title={hod.isActive ? "Click to Deactivate" : "Click to Activate"}
                              className="cursor-pointer"
                            >
                              {hod.isActive ? (
                                <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-200 border-0 text-[10px]">
                                  Active
                                </Badge>
                              ) : (
                                <Badge variant="secondary" className="hover:bg-muted text-[10px]">
                                  Inactive
                                </Badge>
                              )}
                            </button>
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenResetPassword(hod)}
                                className="size-8 p-0 text-amber-600 hover:text-amber-700 hover:bg-amber-50 cursor-pointer"
                                title="Reset Password"
                              >
                                <KeyRound className="size-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenEdit(hod)}
                                className="size-8 p-0 text-muted-foreground hover:text-foreground cursor-pointer"
                                title="Edit HOD Details"
                              >
                                <Edit2 className="size-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setDeleteTarget(hod)}
                                className="size-8 p-0 text-rose-500 hover:text-rose-700 hover:bg-rose-50 cursor-pointer"
                                title="Delete HOD"
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

        {/* Create HOD Dialog */}
        <Dialog open={createModalOpen} onOpenChange={setCreateModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-bold">Create Branch HOD Account</DialogTitle>
              <DialogDescription className="text-xs">
                Assign Head of Department credentials and associate permanently with a branch.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleCreateSubmit} className="space-y-3.5 pt-2">
              <div className="space-y-1">
                <Label htmlFor="hod-branch" className="text-xs font-semibold">
                  Branch Assignment *
                </Label>
                <Select
                  value={createFormData.branchCode}
                  onValueChange={(val) => setCreateFormData({ ...createFormData, branchCode: val })}
                >
                  <SelectTrigger id="hod-branch" className="text-xs">
                    <SelectValue placeholder="Select Branch" />
                  </SelectTrigger>
                  <SelectContent>
                    {(branches || []).map((b) => (
                      <SelectItem key={b.code} value={b.code} className="text-xs">
                        {b.code} — {b.name} {b.hodName ? `(Current HOD: ${b.hodName})` : "(Unassigned)"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <Label htmlFor="hod-name" className="text-xs font-semibold">
                  Full Name *
                </Label>
                <Input
                  id="hod-name"
                  value={createFormData.name}
                  onChange={(e) => setCreateFormData({ ...createFormData, name: e.target.value })}
                  placeholder="e.g. Dr. Ramesh Kumar"
                  className="text-xs"
                  required
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="hod-email" className="text-xs font-semibold">
                  Email ID (Login Username) *
                </Label>
                <Input
                  id="hod-email"
                  type="email"
                  value={createFormData.email}
                  onChange={(e) => setCreateFormData({ ...createFormData, email: e.target.value })}
                  placeholder="hod.cse@college.edu"
                  className="text-xs"
                  required
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="hod-phone" className="text-xs font-semibold">
                  Mobile Number
                </Label>
                <Input
                  id="hod-phone"
                  value={createFormData.phone}
                  onChange={(e) => setCreateFormData({ ...createFormData, phone: e.target.value })}
                  placeholder="+91 9876543210"
                  className="text-xs"
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="hod-password" className="text-xs font-semibold">
                  Initial Password *
                </Label>
                <div className="relative">
                  <Input
                    id="hod-password"
                    type={showCreatePassword ? "text" : "password"}
                    value={createFormData.password}
                    onChange={(e) => setCreateFormData({ ...createFormData, password: e.target.value })}
                    placeholder="Minimum 6 characters"
                    className="text-xs pr-9"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowCreatePassword((v) => !v)}
                    className="absolute inset-y-0 right-0 grid w-9 place-items-center text-muted-foreground hover:text-foreground"
                  >
                    {showCreatePassword ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                  </button>
                </div>
              </div>

              <DialogFooter className="pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setCreateModalOpen(false)}
                  disabled={creating}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={creating}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs gap-1.5"
                >
                  {creating && <Loader2 className="size-3.5 animate-spin" />}
                  Create HOD Account
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Edit HOD Dialog */}
        <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-bold">Edit HOD Details</DialogTitle>
              <DialogDescription className="text-xs">
                Update account information, email, or reassign branch.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleEditSubmit} className="space-y-3.5 pt-2">
              <div className="space-y-1">
                <Label htmlFor="edit-hod-branch" className="text-xs font-semibold">
                  Branch Assignment *
                </Label>
                <Select
                  value={editFormData.branchCode}
                  onValueChange={(val) => setEditFormData({ ...editFormData, branchCode: val })}
                >
                  <SelectTrigger id="edit-hod-branch" className="text-xs">
                    <SelectValue placeholder="Select Branch" />
                  </SelectTrigger>
                  <SelectContent>
                    {(branches || []).map((b) => (
                      <SelectItem key={b.code} value={b.code} className="text-xs">
                        {b.code} — {b.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <Label htmlFor="edit-hod-name" className="text-xs font-semibold">
                  Full Name *
                </Label>
                <Input
                  id="edit-hod-name"
                  value={editFormData.name}
                  onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                  className="text-xs"
                  required
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="edit-hod-email" className="text-xs font-semibold">
                  Email Address *
                </Label>
                <Input
                  id="edit-hod-email"
                  type="email"
                  value={editFormData.email}
                  onChange={(e) => setEditFormData({ ...editFormData, email: e.target.value })}
                  className="text-xs"
                  required
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="edit-hod-phone" className="text-xs font-semibold">
                  Mobile Number
                </Label>
                <Input
                  id="edit-hod-phone"
                  value={editFormData.phone}
                  onChange={(e) => setEditFormData({ ...editFormData, phone: e.target.value })}
                  className="text-xs"
                />
              </div>

              <DialogFooter className="pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setEditModalOpen(false)}
                  disabled={savingEdit}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={savingEdit}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs gap-1.5"
                >
                  {savingEdit && <Loader2 className="size-3.5 animate-spin" />}
                  Save Changes
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Reset Password Dialog */}
        <Dialog open={resetModalOpen} onOpenChange={setResetModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-amber-600 text-base font-bold">
                <KeyRound className="size-4" /> Reset HOD Password
              </DialogTitle>
              <DialogDescription className="text-xs">
                Set a new login password for <strong>{targetResetHod?.name}</strong> (
                {targetResetHod?.email}).
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleResetPasswordSubmit} className="space-y-3.5 pt-2">
              <div className="space-y-1">
                <Label htmlFor="reset-new-password" className="text-xs font-semibold">
                  New Password *
                </Label>
                <div className="relative">
                  <Input
                    id="reset-new-password"
                    type={showNewPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter at least 6 characters"
                    className="text-xs pr-9"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword((v) => !v)}
                    className="absolute inset-y-0 right-0 grid w-9 place-items-center text-muted-foreground hover:text-foreground"
                  >
                    {showNewPassword ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                  </button>
                </div>
              </div>

              <DialogFooter className="pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setResetModalOpen(false)}
                  disabled={resettingPassword}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={resettingPassword}
                  className="bg-amber-600 hover:bg-amber-700 text-white text-xs gap-1.5"
                >
                  {resettingPassword && <Loader2 className="size-3.5 animate-spin" />}
                  Update Password
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
                <AlertTriangle className="size-5" /> Delete HOD Account?
              </AlertDialogTitle>
              <AlertDialogDescription className="text-xs space-y-2">
                <p>
                  Are you sure you want to permanently delete the HOD account for{" "}
                  <strong>{deleteTarget?.name}</strong> ({deleteTarget?.email})?
                </p>
                <p className="text-muted-foreground">
                  Branch {deleteTarget?.branchCode} will become unassigned, but student, mentor, and
                  session records will remain intact.
                </p>
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
