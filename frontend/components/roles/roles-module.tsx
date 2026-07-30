"use client";

import { Pencil, Plus, ShieldCheck, Trash2, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";

type Role = {
  id: string; codigo: string; nombre: string; descripcion: string | null;
  empresa_id: string | null; es_sistema: boolean; estado: string;
  permisos: string[]; usuarios_asignados: number;
};
type Permission = { codigo: string; modulo: string; nombre: string };
const message = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";

export function RolesModule() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [selected, setSelected] = useState<Role | null>(null);
  const [editing, setEditing] = useState<Role | null>(null);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ nombre: "", descripcion: "", permisos: [] as string[] });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [roleData, permissionData] = await Promise.all([
        apiRequest<Role[]>("/roles"),
        apiRequest<Permission[]>("/roles/permisos"),
      ]);
      setRoles(roleData); setPermissions(permissionData);
      setSelected((current) => current ? roleData.find((role) => role.id === current.id) || null : null);
    } catch (requestError) { setError(message(requestError)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  const groups = useMemo(() => Object.entries(Object.groupBy(permissions, (permission) => permission.modulo)), [permissions]);
  const customCount = roles.filter((role) => !role.es_sistema && role.estado === "activo").length;

  function openNew() {
    setEditing(null); setForm({ nombre: "", descripcion: "", permisos: ["dashboard.ver"] }); setModal(true);
  }
  function openEdit(role: Role) {
    setEditing(role); setForm({ nombre: role.nombre, descripcion: role.descripcion || "", permisos: role.permisos }); setModal(true);
  }
  function toggle(permission: string) {
    setForm((current) => ({ ...current, permisos: current.permisos.includes(permission) ? current.permisos.filter((item) => item !== permission) : [...current.permisos, permission] }));
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const body = JSON.stringify({ nombre: form.nombre, descripcion: form.descripcion || null, permisos: form.permisos });
      const role = editing
        ? await apiRequest<Role>(`/roles/${editing.id}`, { method: "PATCH", body })
        : await apiRequest<Role>("/roles", { method: "POST", body });
      setModal(false); await load(); setSelected(role);
    } catch (requestError) { setError(message(requestError)); }
    finally { setSaving(false); }
  }
  async function deactivate(role: Role) {
    if (!window.confirm(`¿Desactivar el rol "${role.nombre}"?`)) return;
    try { await apiRequest<void>(`/roles/${role.id}`, { method: "DELETE" }); setSelected(null); await load(); }
    catch (requestError) { setError(message(requestError)); }
  }

  return <div className="space-y-5">
    <PageHeading title="Roles y permisos" subtitle="Define qué puede ver y realizar cada tipo de usuario de la empresa." action={<button className="button primary" onClick={openNew}><Plus size={16} /> Nuevo rol</button>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    <div className="grid gap-3 sm:grid-cols-3"><Metric label="Roles disponibles" value={roles.filter((role) => role.estado === "activo").length} /><Metric label="Roles personalizados" value={customCount} /><Metric label="Permisos configurables" value={permissions.length} /></div>
    <div className="grid gap-4 xl:grid-cols-[1fr_0.85fr]">
      <section className="space-y-3">{loading ? <Empty text="Cargando roles…" /> : roles.map((role) => <button key={role.id} onClick={() => setSelected(role)} className={`w-full rounded-xl border bg-white p-4 text-left shadow-sm ${selected?.id === role.id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"}`}><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-3"><span className={`rounded-xl p-2 ${role.es_sistema ? "bg-slate-100 text-slate-600" : "bg-blue-50 text-blue-600"}`}><ShieldCheck size={18} /></span><div><strong>{role.nombre}</strong><div className="text-xs text-slate-500">{role.descripcion || "Sin descripción"}</div></div></div><span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-bold">{role.es_sistema ? "Sistema" : "Personalizado"}</span></div><div className="mt-3 flex justify-between text-xs text-slate-500"><span>{role.usuarios_asignados} usuario(s)</span><span>{role.es_sistema ? "Protegido" : `${role.permisos.length} permisos`}</span></div></button>)}</section>
      <section className="rounded-2xl border bg-white p-5 shadow-sm">{!selected ? <div className="flex min-h-80 items-center justify-center text-sm text-slate-500">Selecciona un rol</div> : <><div className="flex items-start justify-between border-b pb-4"><div><h2 className="text-xl font-bold">{selected.nombre}</h2><p className="text-sm text-slate-500">{selected.descripcion || "Sin descripción"}</p></div>{!selected.es_sistema ? <div className="flex gap-2"><button className="button" onClick={() => openEdit(selected)}><Pencil size={14} /> Editar</button><button className="button text-red-600" disabled={selected.usuarios_asignados > 0} onClick={() => void deactivate(selected)} title={selected.usuarios_asignados ? "Tiene usuarios asignados" : "Desactivar"}><Trash2 size={14} /></button></div> : null}</div>{selected.es_sistema ? <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">Este rol forma parte del sistema y está protegido. Puedes asignarlo a usuarios, pero no modificarlo.</div> : <div className="mt-5 space-y-4">{groups.map(([module, options]) => { const enabled = options?.filter((option) => selected.permisos.includes(option.codigo)) || []; return enabled.length ? <div key={module}><div className="text-xs font-bold text-slate-700">{module}</div><div className="mt-2 flex flex-wrap gap-2">{enabled.map((option) => <span key={option.codigo} className="rounded-full bg-blue-50 px-2.5 py-1 text-xs text-blue-700">{option.nombre}</span>)}</div></div> : null; })}</div>}</>}</section>
    </div>
    {modal ? <Modal title={editing ? "Editar rol" : "Nuevo rol"} close={() => setModal(false)}><form className="space-y-5" onSubmit={save}><div className="grid gap-3 sm:grid-cols-2"><Field label="Nombre"><input required minLength={2} className="form-control" value={form.nombre} onChange={(event) => setForm({ ...form, nombre: event.target.value })} /></Field><Field label="Descripción"><input className="form-control" value={form.descripcion} onChange={(event) => setForm({ ...form, descripcion: event.target.value })} /></Field></div><div className="max-h-[52vh] space-y-4 overflow-y-auto pr-2">{groups.map(([module, options]) => <div key={module} className="rounded-xl border p-4"><div className="mb-3 font-bold">{module}</div><div className="grid gap-2 sm:grid-cols-2">{options?.map((permission) => <label key={permission.codigo} className="flex items-center gap-2 rounded-lg bg-slate-50 p-3 text-sm"><input type="checkbox" checked={form.permisos.includes(permission.codigo)} onChange={() => toggle(permission.codigo)} />{permission.nombre}</label>)}</div></div>)}</div><div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={() => setModal(false)}>Cancelar</button><button disabled={saving} className="button primary">{saving ? "Guardando…" : "Guardar rol"}</button></div></form></Modal> : null}
  </div>;
}

function Metric({ label, value }: { label: string; value: number }) { return <div className="rounded-xl border bg-white p-4 shadow-sm"><div className="text-2xl font-black">{value}</div><div className="text-xs text-slate-500">{label}</div></div>; }
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><div className="max-h-[94vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex justify-between border-b bg-white px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
