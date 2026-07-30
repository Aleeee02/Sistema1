"use client";

import { Building2, ClipboardList, Crown, MapPin, Pencil, Phone, Plus, Trash2, UsersRound, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";

type Branch = {
  id: string; empresa_id: string; nombre: string; codigo: string;
  direccion: string | null; telefono: string | null; es_principal: boolean;
  estado: string; created_at: string; empleados_activos: number; ordenes_activas: number;
};
type Form = { nombre: string; codigo: string; direccion: string; telefono: string; es_principal: boolean };
const empty: Form = { nombre: "", codigo: "", direccion: "", telefono: "", es_principal: false };
function message(error: unknown) { return error instanceof ApiError ? error.message : "Ocurrió un error inesperado"; }

export function SucursalesModule() {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selected, setSelected] = useState<Branch | null>(null);
  const [form, setForm] = useState<Form>(empty);
  const [editing, setEditing] = useState<Branch | null>(null);
  const [modal, setModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiRequest<Branch[]>("/sucursales");
      setBranches(data);
      setSelected((current) => current ? data.find((branch) => branch.id === current.id) || null : null);
    } catch (requestError) { setError(message(requestError)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  function openNew() { setEditing(null); setForm(empty); setModal(true); }
  function openEdit(branch: Branch) {
    setEditing(branch);
    setForm({ nombre: branch.nombre, codigo: branch.codigo, direccion: branch.direccion || "", telefono: branch.telefono || "", es_principal: branch.es_principal });
    setModal(true);
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const branch = await apiRequest<Branch>(editing ? `/sucursales/${editing.id}` : "/sucursales", {
        method: editing ? "PATCH" : "POST",
        body: JSON.stringify({ ...form, direccion: form.direccion || null, telefono: form.telefono || null }),
      });
      setModal(false); await load(); setSelected(branch);
    } catch (requestError) { setError(message(requestError)); }
    finally { setSaving(false); }
  }
  async function makePrincipal(branch: Branch) {
    try { const updated = await apiRequest<Branch>(`/sucursales/${branch.id}`, { method: "PATCH", body: JSON.stringify({ es_principal: true }) }); await load(); setSelected(updated); }
    catch (requestError) { setError(message(requestError)); }
  }
  async function deactivate(branch: Branch) {
    if (!window.confirm(`¿Desactivar la sucursal ${branch.nombre}?`)) return;
    try { await apiRequest<void>(`/sucursales/${branch.id}`, { method: "DELETE" }); setSelected(null); await load(); }
    catch (requestError) { setError(message(requestError)); }
  }

  return <div className="space-y-5">
    <PageHeading title="Sucursales" subtitle="Sedes operativas, personal y órdenes de la empresa." action={<button className="button primary" onClick={openNew}><Plus size={16} /> Nueva sucursal</button>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    {loading ? <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">Cargando sucursales…</div> : branches.length === 0 ? <div className="rounded-xl border border-dashed bg-white p-12 text-center"><Building2 className="mx-auto mb-3 text-blue-600" /><h2 className="font-semibold">Crea la primera sucursal</h2></div> :
    <div className="grid gap-4 xl:grid-cols-[0.9fr_1.15fr]">
      <section className="grid content-start gap-3 sm:grid-cols-2 xl:grid-cols-1">{branches.map((branch) =>
        <button key={branch.id} onClick={() => setSelected(branch)} className={`rounded-2xl border bg-white p-4 text-left shadow-sm ${selected?.id === branch.id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200 hover:border-slate-300"}`}>
          <div className="flex items-start justify-between"><span className="grid size-11 place-items-center rounded-xl bg-blue-50 text-blue-600"><Building2 size={21} /></span>{branch.es_principal ? <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-[10px] font-bold text-amber-700"><Crown size={11} /> Principal</span> : null}</div>
          <h3 className="mt-3 font-bold">{branch.nombre}</h3><p className="mt-1 text-xs text-slate-500">{branch.codigo} · {branch.direccion || "Sin dirección"}</p>
          <div className="mt-4 flex gap-4 text-xs text-slate-500"><span>{branch.empleados_activos} empleados</span><span>{branch.ordenes_activas} OT activas</span></div>
        </button>)}</section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">{!selected ? <div className="flex min-h-96 items-center justify-center text-sm text-slate-500">Selecciona una sucursal</div> :
        <>
          <div className="flex flex-wrap justify-between gap-3 border-b pb-5"><div><div className="flex items-center gap-2"><h2 className="text-xl font-bold">{selected.nombre}</h2>{selected.es_principal ? <Crown size={17} className="text-amber-500" /> : null}</div><p className="mt-1 font-mono text-xs text-slate-500">{selected.codigo}</p></div><div className="flex gap-2"><button className="button" onClick={() => openEdit(selected)}><Pencil size={15} /> Editar</button>{!selected.es_principal ? <button className="button text-red-600" onClick={() => void deactivate(selected)}><Trash2 size={15} /></button> : null}</div></div>
          <div className="grid gap-3 py-5 sm:grid-cols-2"><Info icon={<MapPin size={17} />} label="Dirección" value={selected.direccion || "No registrada"} /><Info icon={<Phone size={17} />} label="Teléfono" value={selected.telefono || "No registrado"} /><Info icon={<UsersRound size={17} />} label="Empleados activos" value={String(selected.empleados_activos)} /><Info icon={<ClipboardList size={17} />} label="Órdenes activas" value={String(selected.ordenes_activas)} /></div>
          {!selected.es_principal ? <button className="button" onClick={() => void makePrincipal(selected)}><Crown size={15} /> Establecer como principal</button> : <div className="rounded-xl bg-amber-50 p-4 text-sm text-amber-800">Esta es la sede principal de la empresa.</div>}
        </>}</section>
    </div>}
    {modal ? <Modal title={editing ? "Editar sucursal" : "Nueva sucursal"} close={() => setModal(false)}><form className="space-y-4" onSubmit={save}><div className="grid gap-3 sm:grid-cols-2"><Field label="Nombre"><input required className="form-control" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></Field><Field label="Código"><input required className="form-control uppercase" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} /></Field></div><Field label="Dirección"><input className="form-control" value={form.direccion} onChange={(e) => setForm({ ...form, direccion: e.target.value })} /></Field><Field label="Teléfono"><input className="form-control" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} /></Field>{!editing?.es_principal ? <label className="flex items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={form.es_principal} onChange={(e) => setForm({ ...form, es_principal: e.target.checked })} />Establecer como sucursal principal</label> : null}<div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={() => setModal(false)}>Cancelar</button><button disabled={saving} className="button primary">{saving ? "Guardando…" : "Guardar sucursal"}</button></div></form></Modal> : null}
  </div>;
}
function Info({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="flex gap-3 rounded-xl bg-slate-50 p-3"><span className="text-slate-400">{icon}</span><div><div className="text-[10px] font-bold uppercase text-slate-400">{label}</div><div className="text-sm font-semibold">{value}</div></div></div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}><div className="w-full max-w-xl rounded-2xl bg-white shadow-2xl"><div className="flex justify-between border-b px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
