"use client";

import { BriefcaseBusiness, MapPin, Pencil, Phone, Plus, Search, Trash2, UserRound, Wrench, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";

export type Empleado = {
  id: string; codigo: string; nombres: string; apellidos: string; cargo: string;
  especialidad: string | null; telefono: string | null; estado: string;
  sucursal_id: string | null; sucursal_nombre: string | null; created_at: string;
};
type Branch = { id: string; nombre: string; es_principal: boolean };
type Form = { codigo: string; nombres: string; apellidos: string; cargo: string; especialidad: string; telefono: string; sucursal_id: string };
const empty: Form = { codigo: "", nombres: "", apellidos: "", cargo: "Mecánico", especialidad: "", telefono: "", sucursal_id: "" };
function message(error: unknown) { return error instanceof ApiError ? error.message : "Ocurrió un error inesperado"; }

export function EmpleadosModule() {
  const [employees, setEmployees] = useState<Empleado[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selected, setSelected] = useState<Empleado | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Empleado | null>(null);
  const [form, setForm] = useState<Form>(empty);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [staff, options] = await Promise.all([
        apiRequest<Empleado[]>("/empleados"),
        apiRequest<{ sucursales: Branch[] }>("/ordenes/opciones"),
      ]);
      setEmployees(staff); setBranches(options.sucursales);
      setSelected((current) => current ? staff.find((employee) => employee.id === current.id) || null : null);
    } catch (requestError) { setError(message(requestError)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  const visible = useMemo(() => {
    const term = search.toLowerCase().trim();
    return term ? employees.filter((employee) => `${employee.codigo} ${employee.nombres} ${employee.apellidos} ${employee.cargo} ${employee.especialidad}`.toLowerCase().includes(term)) : employees;
  }, [employees, search]);
  const mechanics = employees.filter((employee) => employee.cargo.toLowerCase().includes("mec")).length;

  function openNew() { setEditing(null); setForm({ ...empty, sucursal_id: branches[0]?.id || "" }); setModal(true); }
  function openEdit(employee: Empleado) {
    setEditing(employee);
    setForm({ codigo: employee.codigo, nombres: employee.nombres, apellidos: employee.apellidos, cargo: employee.cargo, especialidad: employee.especialidad || "", telefono: employee.telefono || "", sucursal_id: employee.sucursal_id || "" });
    setModal(true);
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const payload = editing
        ? { codigo: form.codigo, nombres: form.nombres, apellidos: form.apellidos, cargo: form.cargo, especialidad: form.especialidad || null, telefono: form.telefono || null }
        : { ...form, especialidad: form.especialidad || null, telefono: form.telefono || null };
      const employee = await apiRequest<Empleado>(editing ? `/empleados/${editing.id}` : "/empleados", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
      setModal(false); await load(); setSelected(employee);
    } catch (requestError) { setError(message(requestError)); }
    finally { setSaving(false); }
  }
  async function deactivate(employee: Empleado) {
    if (!window.confirm(`¿Desactivar a ${employee.nombres} ${employee.apellidos}?`)) return;
    try { await apiRequest<void>(`/empleados/${employee.id}`, { method: "DELETE" }); setSelected(null); await load(); }
    catch (requestError) { setError(message(requestError)); }
  }

  return <div className="space-y-5">
    <PageHeading title="Empleados" subtitle="Equipo del taller, especialidades y sucursal principal." action={<button className="button primary" onClick={openNew}><Plus size={16} /> Nuevo empleado</button>} />
    <div className="grid gap-3 sm:grid-cols-3">
      <Metric icon={<UserRound size={19} />} label="Empleados activos" value={employees.length} />
      <Metric icon={<Wrench size={19} />} label="Mecánicos" value={mechanics} />
      <Metric icon={<MapPin size={19} />} label="Sucursales con personal" value={new Set(employees.map((employee) => employee.sucursal_id).filter(Boolean)).size} />
    </div>
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    <div className="grid min-h-[550px] gap-4 xl:grid-cols-[0.9fr_1.2fr]">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b p-4"><label className="flex items-center gap-2 rounded-xl bg-slate-50 px-3"><Search size={17} className="text-slate-400" /><input className="h-11 w-full bg-transparent text-sm outline-none" placeholder="Nombre, código, cargo o especialidad" value={search} onChange={(e) => setSearch(e.target.value)} /></label></div>
        <div className="max-h-[650px] overflow-y-auto p-2">{loading ? <Empty text="Cargando empleados…" /> : visible.length === 0 ? <Empty text="No hay empleados registrados." /> : visible.map((employee) =>
          <button key={employee.id} onClick={() => setSelected(employee)} className={`mb-1 flex w-full items-center gap-3 rounded-xl p-3 text-left ${selected?.id === employee.id ? "bg-blue-50 ring-1 ring-blue-200" : "hover:bg-slate-50"}`}>
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-slate-900 text-xs font-bold text-white">{employee.nombres[0]}{employee.apellidos[0]}</span>
            <span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{employee.nombres} {employee.apellidos}</span><span className="block truncate text-xs text-slate-500">{employee.codigo} · {employee.cargo}</span></span>
          </button>)}</div>
      </section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        {!selected ? <div className="flex h-full min-h-96 flex-col items-center justify-center text-center"><span className="mb-4 rounded-2xl bg-blue-50 p-4 text-blue-600"><UserRound size={30} /></span><h2 className="font-semibold">Selecciona un empleado</h2></div> :
        <>
          <div className="flex flex-wrap justify-between gap-3 border-b pb-5"><div><h2 className="text-xl font-bold">{selected.nombres} {selected.apellidos}</h2><p className="mt-1 text-sm text-slate-500">{selected.codigo}</p></div><div className="flex gap-2"><button className="button" onClick={() => openEdit(selected)}><Pencil size={15} /> Editar</button><button className="button text-red-600" onClick={() => void deactivate(selected)}><Trash2 size={15} /></button></div></div>
          <div className="grid gap-3 py-5 sm:grid-cols-2"><Info icon={<BriefcaseBusiness size={16} />} label="Cargo" value={selected.cargo} /><Info icon={<Wrench size={16} />} label="Especialidad" value={selected.especialidad || "No registrada"} /><Info icon={<Phone size={16} />} label="Teléfono" value={selected.telefono || "No registrado"} /><Info icon={<MapPin size={16} />} label="Sucursal principal" value={selected.sucursal_nombre || "Sin asignar"} /></div>
          <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4"><div className="text-xs font-bold uppercase tracking-wide text-emerald-700">Estado activo</div><p className="mt-1 text-sm text-emerald-800">Disponible para asignarse a órdenes de su sucursal.</p></div>
        </>}
      </section>
    </div>
    {modal ? <Modal title={editing ? "Editar empleado" : "Nuevo empleado"} close={() => setModal(false)}><form className="space-y-4" onSubmit={save}>
      <div className="grid gap-3 sm:grid-cols-2"><Field label="Código"><input required className="form-control uppercase" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} /></Field><Field label="Sucursal principal"><select required disabled={Boolean(editing)} className="form-control" value={form.sucursal_id} onChange={(e) => setForm({ ...form, sucursal_id: e.target.value })}><option value="">Seleccionar</option>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.nombre}</option>)}</select></Field><Field label="Nombres"><input required className="form-control" value={form.nombres} onChange={(e) => setForm({ ...form, nombres: e.target.value })} /></Field><Field label="Apellidos"><input required className="form-control" value={form.apellidos} onChange={(e) => setForm({ ...form, apellidos: e.target.value })} /></Field><Field label="Cargo"><input required className="form-control" value={form.cargo} onChange={(e) => setForm({ ...form, cargo: e.target.value })} /></Field><Field label="Especialidad"><input className="form-control" placeholder="Motor, frenos, electricidad…" value={form.especialidad} onChange={(e) => setForm({ ...form, especialidad: e.target.value })} /></Field></div>
      <Field label="Teléfono"><input className="form-control" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} /></Field>
      <div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={() => setModal(false)}>Cancelar</button><button disabled={saving} className="button primary">{saving ? "Guardando…" : "Guardar empleado"}</button></div>
    </form></Modal> : null}
  </div>;
}
function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) { return <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><span className="rounded-xl bg-blue-50 p-2.5 text-blue-600">{icon}</span><div><div className="text-2xl font-bold">{value}</div><div className="text-xs text-slate-500">{label}</div></div></div>; }
function Info({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="flex gap-3 rounded-xl bg-slate-50 p-3"><span className="text-slate-400">{icon}</span><div><div className="text-[10px] font-bold uppercase text-slate-400">{label}</div><div className="text-sm font-semibold">{value}</div></div></div>; }
function Empty({ text }: { text: string }) { return <div className="p-10 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}><div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex justify-between border-b bg-white px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
