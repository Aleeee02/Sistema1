"use client";

import { Clock3, Pencil, Plus, Search, Trash2, Wrench, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";

type Service = { id: string; codigo: string; nombre: string; descripcion: string | null; categoria: string | null; precio_referencia: string; duracion_minutos: number | null };
type Form = { codigo: string; nombre: string; descripcion: string; categoria: string; precio_referencia: string; duracion_minutos: string };
const empty: Form = { codigo: "", nombre: "", descripcion: "", categoria: "", precio_referencia: "0", duracion_minutos: "" };
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";

export function ServiciosModule() {
  const [services, setServices] = useState<Service[]>([]);
  const [selected, setSelected] = useState<Service | null>(null);
  const [editing, setEditing] = useState<Service | null>(null);
  const [form, setForm] = useState<Form>(empty);
  const [search, setSearch] = useState("");
  const [modal, setModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    try { setServices(await apiRequest<Service[]>("/servicios")); }
    catch (requestError) { setError(errorText(requestError)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);
  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return !term ? services : services.filter((service) => [service.codigo, service.nombre, service.categoria].some((value) => value?.toLowerCase().includes(term)));
  }, [search, services]);
  const average = services.length ? services.reduce((sum, service) => sum + Number(service.precio_referencia), 0) / services.length : 0;

  function openNew() { setEditing(null); setForm(empty); setModal(true); }
  function openEdit(service: Service) {
    setEditing(service);
    setForm({ codigo: service.codigo, nombre: service.nombre, descripcion: service.descripcion || "", categoria: service.categoria || "", precio_referencia: service.precio_referencia, duracion_minutos: service.duracion_minutos?.toString() || "" });
    setModal(true);
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    const payload = { ...form, descripcion: form.descripcion || null, categoria: form.categoria || null, precio_referencia: Number(form.precio_referencia), duracion_minutos: form.duracion_minutos ? Number(form.duracion_minutos) : null };
    try {
      await apiRequest<Service>(editing ? `/servicios/${editing.id}` : "/servicios", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
      setModal(false); setSelected(null); await load();
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setSaving(false); }
  }
  async function deactivate(service: Service) {
    if (!window.confirm(`¿Desactivar ${service.nombre}?`)) return;
    try { await apiRequest<void>(`/servicios/${service.id}`, { method: "DELETE" }); setSelected(null); await load(); }
    catch (requestError) { setError(errorText(requestError)); }
  }

  return <div className="space-y-5">
    <PageHeading title="Catálogo de servicios" subtitle="Mano de obra, precios y tiempos de referencia para cotizaciones." action={<button className="button primary" onClick={openNew}><Plus size={16} /> Nuevo servicio</button>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    <div className="grid gap-3 sm:grid-cols-3"><Metric icon={<Wrench size={19} />} label="Servicios activos" value={String(services.length)} /><Metric icon={<Clock3 size={19} />} label="Con tiempo estimado" value={String(services.filter((service) => service.duracion_minutos).length)} /><Metric icon={<b>S/</b>} label="Precio promedio" value={average.toFixed(2)} /></div>
    <label className="flex items-center gap-2 rounded-xl border bg-white px-4 shadow-sm"><Search size={17} className="text-slate-400" /><input className="h-12 w-full bg-transparent text-sm outline-none" placeholder="Buscar por código, nombre o categoría" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    <div className="grid gap-4 xl:grid-cols-[1fr_1.05fr]">
      <section className="grid content-start gap-3">{loading ? <Empty text="Cargando servicios…" /> : filtered.length === 0 ? <Empty text="No hay servicios registrados." /> : filtered.map((service) => <button key={service.id} onClick={() => setSelected(service)} className={`rounded-xl border bg-white p-4 text-left shadow-sm ${selected?.id === service.id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"}`}><div className="flex justify-between"><span className="font-mono text-xs font-bold text-blue-700">{service.codigo}</span><span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-bold">{service.categoria || "General"}</span></div><h3 className="mt-2 font-semibold">{service.nombre}</h3><div className="mt-3 flex justify-between text-sm"><strong>S/ {Number(service.precio_referencia).toFixed(2)}</strong><span className="text-slate-500">{service.duracion_minutos ? `${service.duracion_minutos} min` : "Sin tiempo definido"}</span></div></button>)}</section>
      <section className="rounded-2xl border bg-white p-5 shadow-sm">{!selected ? <div className="flex min-h-80 items-center justify-center text-sm text-slate-500">Selecciona un servicio</div> : <><div className="flex justify-between border-b pb-5"><div><span className="font-mono text-xs font-bold text-blue-700">{selected.codigo}</span><h2 className="mt-1 text-xl font-bold">{selected.nombre}</h2></div><div className="flex gap-2"><button className="button" onClick={() => openEdit(selected)}><Pencil size={15} /> Editar</button><button className="button text-red-600" onClick={() => void deactivate(selected)}><Trash2 size={15} /></button></div></div><div className="grid gap-3 py-5 sm:grid-cols-2"><Info label="Categoría" value={selected.categoria || "General"} /><Info label="Precio" value={`S/ ${Number(selected.precio_referencia).toFixed(2)}`} /><Info label="Duración" value={selected.duracion_minutos ? `${selected.duracion_minutos} minutos` : "No definida"} /></div><p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{selected.descripcion || "Sin descripción adicional."}</p></>}</section>
    </div>
    {modal ? <Modal close={() => setModal(false)} title={editing ? "Editar servicio" : "Nuevo servicio"}><form className="space-y-4" onSubmit={save}><div className="grid gap-3 sm:grid-cols-2"><Field label="Código"><input required className="form-control uppercase" value={form.codigo} onChange={(event) => setForm({ ...form, codigo: event.target.value })} /></Field><Field label="Nombre"><input required minLength={2} className="form-control" value={form.nombre} onChange={(event) => setForm({ ...form, nombre: event.target.value })} /></Field><Field label="Categoría"><input className="form-control" value={form.categoria} onChange={(event) => setForm({ ...form, categoria: event.target.value })} /></Field><Field label="Precio de referencia"><input required type="number" min="0" step="0.01" className="form-control" value={form.precio_referencia} onChange={(event) => setForm({ ...form, precio_referencia: event.target.value })} /></Field><Field label="Duración (minutos)"><input type="number" min="1" className="form-control" value={form.duracion_minutos} onChange={(event) => setForm({ ...form, duracion_minutos: event.target.value })} /></Field></div><Field label="Descripción"><textarea className="form-control min-h-24" value={form.descripcion} onChange={(event) => setForm({ ...form, descripcion: event.target.value })} /></Field><div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={() => setModal(false)}>Cancelar</button><button disabled={saving} className="button primary">{saving ? "Guardando…" : "Guardar servicio"}</button></div></form></Modal> : null}
  </div>;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm"><span className="rounded-xl bg-blue-50 p-2.5 text-blue-600">{icon}</span><div><div className="text-xl font-bold">{value}</div><div className="text-xs text-slate-500">{label}</div></div></div>; }
function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-slate-50 p-3"><div className="text-[10px] font-bold uppercase text-slate-400">{label}</div><div className="mt-1 font-semibold">{value}</div></div>; }
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="flex justify-between border-b px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
