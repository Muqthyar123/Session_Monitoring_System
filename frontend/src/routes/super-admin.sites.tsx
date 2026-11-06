import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Building2,
  Plus,
  Search,
  Edit2,
  Trash2,
  MapPin,
  Mail,
  Phone,
  GitBranch,
  AlertTriangle,
  Loader2,
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  getSites,
  createSite,
  updateSite,
  deleteSite,
} from "@/services/superAdminService";
import type { Site } from "@/data/mock/mockData";

export const Route = createFileRoute("/super-admin/sites")({
  head: () => ({
    meta: [
      { title: "Sites & Campuses — Super Admin" },
      { name: "description", content: "Manage institutional campuses and college sites." },
    ],
  }),
  component: SuperAdminSitesPage,
});

function SuperAdminSitesPage() {
  const { data: sites, loading, error, reload } = useAsyncData(() => getSites(), []);
  const [searchTerm, setSearchTerm] = useState("");

  // Create / Edit modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSite, setEditingSite] = useState<Site | null>(null);
  const [formData, setFormData] = useState({
    code: "",
    name: "",
    location: "",
    address: "",
    contactEmail: "",
    contactPhone: "",
    description: "",
    isActive: true,
  });
  const [saving, setSaving] = useState(false);

  // Delete modal state
  const [deleteTarget, setDeleteTarget] = useState<Site | null>(null);
  const [deleting, setDeleting] = useState(false);

  const filteredSites = (sites || []).filter((s) => {
    const q = searchTerm.toLowerCase();
    return (
      s.name.toLowerCase().includes(q) ||
      s.code.toLowerCase().includes(q) ||
      (s.location && s.location.toLowerCase().includes(q))
    );
  });

  const handleOpenCreate = () => {
    setEditingSite(null);
    setFormData({
      code: "",
      name: "",
      location: "",
      address: "",
      contactEmail: "",
      contactPhone: "",
      description: "",
      isActive: true,
    });
    setModalOpen(true);
  };

  const handleOpenEdit = (site: Site) => {
    setEditingSite(site);
    setFormData({
      code: site.code,
      name: site.name,
      location: site.location || "",
      address: site.address || "",
      contactEmail: site.contactEmail || "",
      contactPhone: site.contactPhone || "",
      description: site.description || "",
      isActive: site.isActive,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.code.trim() || !formData.name.trim()) {
      toast.error("Code and Name are required");
      return;
    }

    setSaving(true);
    try {
      if (editingSite) {
        await updateSite(editingSite.id, formData);
        toast.success(`Site "${formData.name}" updated successfully`);
      } else {
        await createSite(formData);
        toast.success(`Site "${formData.name}" created successfully`);
      }
      setModalOpen(false);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save site");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteSite(deleteTarget.id);
      toast.success(`Site "${deleteTarget.name}" deleted successfully`);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete site");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <PageHeader
            title="Campuses &amp; Sites"
            description="Manage college institutional campus sites and locations hosting branches"
          />
          <Button
            onClick={handleOpenCreate}
            className="gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs cursor-pointer"
          >
            <Plus className="size-3.5" /> Add Campus Site
          </Button>
        </div>

        {/* Search Bar */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
            <Input
              placeholder="Search campuses by name, code, or location..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 text-xs"
            />
          </div>
        </div>

        {/* Content */}
        {loading && !sites && <LoadingState label="Loading campus sites..." />}
        {error && !sites && <ErrorState message={error ?? undefined} onRetry={reload} />}

        {sites && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredSites.length === 0 ? (
              <div className="col-span-full">
                <EmptyState
                  title="No campus sites found"
                  description={
                    searchTerm
                      ? `No sites match "${searchTerm}".`
                      : "Create your first campus site to house institutional branches."
                  }
                  action={
                    !searchTerm ? (
                      <Button onClick={handleOpenCreate} size="sm" className="mt-2 text-xs">
                        Add Campus Site
                      </Button>
                    ) : undefined
                  }
                />
              </div>
            ) : (
              filteredSites.map((site) => (
                <Card key={site.id} className="border-border hover:shadow-md transition-shadow flex flex-col justify-between">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <div className="flex size-10 items-center justify-center rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 border border-indigo-200/50">
                          <Building2 className="size-5" />
                        </div>
                        <div>
                          <CardTitle className="text-base font-bold text-foreground">
                            {site.name}
                          </CardTitle>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <Badge variant="outline" className="font-mono text-[10px] text-indigo-600 bg-indigo-50/50">
                              {site.code}
                            </Badge>
                            {site.isActive ? (
                              <Badge className="bg-emerald-100 text-emerald-800 text-[10px] border-0">
                                Active
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="text-[10px]">
                                Inactive
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                    {site.description && (
                      <CardDescription className="text-xs mt-2 line-clamp-2">
                        {site.description}
                      </CardDescription>
                    )}
                  </CardHeader>

                  <CardContent className="space-y-3 pt-0 text-xs">
                    <div className="space-y-1.5 border-t border-border/60 pt-3">
                      {site.location && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <MapPin className="size-3.5 text-muted-foreground shrink-0" />
                          <span className="truncate">{site.location}</span>
                        </div>
                      )}
                      {site.contactEmail && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Mail className="size-3.5 text-muted-foreground shrink-0" />
                          <span className="truncate">{site.contactEmail}</span>
                        </div>
                      )}
                      {site.contactPhone && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Phone className="size-3.5 text-muted-foreground shrink-0" />
                          <span className="truncate">{site.contactPhone}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between border-t border-border/60 pt-3">
                      <div className="flex items-center gap-1.5 text-indigo-600 font-semibold">
                        <GitBranch className="size-3.5" />
                        <span>{site.branchesCount ?? site.branchCount ?? 0} Branches</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenEdit(site)}
                          className="size-8 p-0 text-muted-foreground hover:text-foreground cursor-pointer"
                          title="Edit Site"
                        >
                          <Edit2 className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteTarget(site)}
                          className="size-8 p-0 text-rose-500 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/20 cursor-pointer"
                          title="Delete Site"
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}

        {/* Create / Edit Dialog */}
        <Dialog open={modalOpen} onOpenChange={setModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-bold">
                {editingSite ? "Edit Campus Site" : "Add New Campus Site"}
              </DialogTitle>
              <DialogDescription className="text-xs">
                Configure institutional campus site details and locations.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-3.5 pt-2">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="site-code" className="text-xs font-semibold">
                    Site Code *
                  </Label>
                  <Input
                    id="site-code"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    placeholder="MAIN"
                    disabled={Boolean(editingSite)}
                    className="text-xs font-mono uppercase"
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="site-name" className="text-xs font-semibold">
                    Campus Name *
                  </Label>
                  <Input
                    id="site-name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Main Campus"
                    className="text-xs"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="site-location" className="text-xs font-semibold">
                  Location / City
                </Label>
                <Input
                  id="site-location"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  placeholder="e.g. Hyderabad, Telangana"
                  className="text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="site-email" className="text-xs font-semibold">
                    Contact Email
                  </Label>
                  <Input
                    id="site-email"
                    type="email"
                    value={formData.contactEmail}
                    onChange={(e) => setFormData({ ...formData, contactEmail: e.target.value })}
                    placeholder="campus@college.edu"
                    className="text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="site-phone" className="text-xs font-semibold">
                    Contact Phone
                  </Label>
                  <Input
                    id="site-phone"
                    value={formData.contactPhone}
                    onChange={(e) => setFormData({ ...formData, contactPhone: e.target.value })}
                    placeholder="+91 9876543210"
                    className="text-xs"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="site-desc" className="text-xs font-semibold">
                  Description
                </Label>
                <Textarea
                  id="site-desc"
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Primary campus housing technical and engineering branches..."
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
                  {editingSite ? "Save Changes" : "Create Site"}
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
                <AlertTriangle className="size-5" /> Delete Campus Site?
              </AlertDialogTitle>
              <AlertDialogDescription className="text-xs space-y-2">
                <p>
                  Are you sure you want to delete <strong>{deleteTarget?.name}</strong> ({deleteTarget?.code})?
                </p>
                {deleteTarget && ((deleteTarget.branchesCount ?? deleteTarget.branchCount ?? 0) > 0) && (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded text-amber-800 dark:text-amber-300 font-medium text-xs">
                    Warning: This site currently has <strong>{deleteTarget.branchesCount ?? deleteTarget.branchCount}</strong> associated branches.
                    You must reassign or remove those branches before deleting this site.
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
