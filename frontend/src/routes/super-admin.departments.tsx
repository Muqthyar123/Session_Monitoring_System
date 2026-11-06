import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Building2, Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { SuperAdminLayout } from "@/layouts/SuperAdminLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getBranches, type Branch } from "@/services/superAdminService";
import { createDepartment, deleteDepartment, getDepartments, updateDepartment, type Department } from "@/services/departmentService";

export const Route = createFileRoute("/super-admin/departments")({ component: SuperAdminDepartmentsPage });

function SuperAdminDepartmentsPage() {
  const [items, setItems] = useState<Department[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [editing, setEditing] = useState<Department | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [branchId, setBranchId] = useState("");
  const [years, setYears] = useState("1st Year, 2nd Year, 3rd Year, 4th Year");
  const [busy, setBusy] = useState(false);
  const load = async () => {
    try { const [d, b] = await Promise.all([getDepartments(), getBranches()]); setItems(d); setBranches(b); }
    catch (e) { toast.error(e instanceof Error ? e.message : "Could not load departments"); }
  };
  useEffect(() => { void load(); }, []);
  const reset = () => { setEditing(null); setCode(""); setName(""); setBranchId(""); setYears("1st Year, 2nd Year, 3rd Year, 4th Year"); };
  const save = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true);
    const parent = branches.find((b) => b.id === branchId);
    const payload = { code: code.trim().toUpperCase(), name: name.trim(), branchId, branchCode: parent?.code, academicYears: years.split(",").map((v) => v.trim()).filter(Boolean) };
    try { if (editing) await updateDepartment(editing.id, payload); else await createDepartment(payload); toast.success("Department saved"); reset(); await load(); }
    catch (e) { toast.error(e instanceof Error ? e.message : "Could not save department"); }
    finally { setBusy(false); }
  };
  const edit = (d: Department) => { setEditing(d); setCode(d.code); setName(d.name); setBranchId(d.branchId || ""); setYears((d.academicYears || []).join(", ")); };
  const remove = async (d: Department) => { if (!window.confirm(`Delete or deactivate ${d.name}?`)) return; try { await deleteDepartment(d.id); toast.success("Department removed"); await load(); } catch (e) { toast.error(e instanceof Error ? e.message : "Could not remove department"); } };

  return <SuperAdminLayout><div className="mx-auto max-w-6xl space-y-6">
    <header><h1 className="flex items-center gap-2 text-2xl font-bold"><Building2 className="size-6"/>Departments</h1><p className="mt-1 text-sm text-muted-foreground">Create departments under a branch and configure their academic years.</p></header>
    <form onSubmit={save} className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-5">
      <Input placeholder="Department code" value={code} onChange={(e) => setCode(e.target.value)} required />
      <Input placeholder="Department name" value={name} onChange={(e) => setName(e.target.value)} required />
      <select className="h-10 rounded-md border bg-background px-3 text-sm" value={branchId} onChange={(e) => setBranchId(e.target.value)} required><option value="">Parent branch</option>{branches.map((b) => <option key={b.id} value={b.id}>{b.code} — {b.name}</option>)}</select>
      <Input placeholder="Years, comma separated" value={years} onChange={(e) => setYears(e.target.value)} required />
      <div className="flex gap-2"><Button disabled={busy} type="submit"><Plus className="mr-1 size-4"/>{editing ? "Save" : "Add"}</Button>{editing && <Button type="button" variant="outline" onClick={reset}>Cancel</Button>}</div>
    </form>
    <div className="overflow-x-auto rounded-lg border bg-card"><table className="w-full text-left text-sm"><thead className="bg-muted/50"><tr><th className="p-3">Department</th><th className="p-3">Branch</th><th className="p-3">Configured years</th><th className="p-3">Students</th><th className="p-3">Actions</th></tr></thead><tbody>{items.map((d) => <tr key={d.id} className="border-t"><td className="p-3"><b>{d.code}</b><div className="text-xs text-muted-foreground">{d.name}</div></td><td className="p-3">{d.branchCode || branches.find((b) => b.id === d.branchId)?.code || "Unassigned"}</td><td className="p-3">{(d.academicYears || []).join(", ")}</td><td className="p-3">{d.studentCount || 0}</td><td className="p-3"><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => edit(d)}><Pencil className="size-3.5"/></Button><Button size="sm" variant="destructive" onClick={() => void remove(d)}><Trash2 className="size-3.5"/></Button></div></td></tr>)}{!items.length && <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">Create a branch first, then add its departments.</td></tr>}</tbody></table></div>
  </div></SuperAdminLayout>;
}
