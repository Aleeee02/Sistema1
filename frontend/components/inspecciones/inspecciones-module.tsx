"use client";

import { Camera, CheckCircle2, ClipboardCheck, Plus, Upload, X } from "lucide-react";
import Image from "next/image";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";
import type { OrdenTrabajo } from "@/types";

type Item = { id?: string; codigo: string; nombre: string; estado: string; observacion: string; orden_visual?: number };
type FileData = { id: string; nombre_original: string; url: string | null; created_at: string };
type Inspection = { id: string; orden_id: string; tipo: string; kilometraje: number | null; nivel_combustible: number | null; observaciones: string | null; confirmada_at: string | null; created_at: string; items: Item[]; archivos: FileData[] };
const initialItems: Item[] = [
  { codigo: "carroceria", nombre: "Carrocería y pintura", estado: "bueno", observacion: "" },
  { codigo: "luces", nombre: "Luces exteriores", estado: "bueno", observacion: "" },
  { codigo: "llantas", nombre: "Llantas y aros", estado: "bueno", observacion: "" },
  { codigo: "vidrios", nombre: "Vidrios y espejos", estado: "bueno", observacion: "" },
  { codigo: "interior", nombre: "Interior y accesorios", estado: "bueno", observacion: "" },
  { codigo: "herramientas", nombre: "Herramientas y objetos", estado: "bueno", observacion: "" },
];
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";

export function InspeccionesModule() {
  const [orders, setOrders] = useState<OrdenTrabajo[]>([]);
  const [orderId, setOrderId] = useState("");
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [selected, setSelected] = useState<Inspection | null>(null);
  const [modal, setModal] = useState(false);
  const [type, setType] = useState("recepcion");
  const [mileage, setMileage] = useState("");
  const [fuel, setFuel] = useState("50");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<Item[]>(initialItems);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadInspections = useCallback(async (id: string) => {
    if (!id) { setInspections([]); setSelected(null); return; }
    try { const data = await apiRequest<Inspection[]>(`/inspecciones/orden/${id}`); setInspections(data); setSelected((current) => current ? data.find((value) => value.id === current.id) || data[0] || null : data[0] || null); }
    catch (requestError) { setError(errorText(requestError)); }
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try { const data = await apiRequest<OrdenTrabajo[]>("/ordenes?limit=100"); setOrders(data); const first = data[0]?.id || ""; setOrderId(first); if (first) await loadInspections(first); }
      catch (requestError) { setError(errorText(requestError)); }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadInspections]);
  function openNew() {
    const order = orders.find((value) => value.id === orderId);
    setType("recepcion"); setMileage(order?.kilometraje?.toString() || ""); setFuel(order?.nivel_combustible?.toString() || "50"); setNotes(""); setItems(initialItems.map((item) => ({ ...item }))); setModal(true);
  }
  function updateItem(index: number, patch: Partial<Item>) { setItems((current) => current.map((item, position) => position === index ? { ...item, ...patch } : item)); }
  async function create(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const inspection = await apiRequest<Inspection>("/inspecciones", { method: "POST", body: JSON.stringify({ orden_id: orderId, tipo: type, kilometraje: mileage ? Number(mileage) : null, nivel_combustible: fuel ? Number(fuel) : null, observaciones: notes || null, items: items.map(({ codigo, nombre, estado, observacion }) => ({ codigo, nombre, estado, observacion: observacion || null })) }) });
      setModal(false); await loadInspections(orderId); setSelected(inspection);
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setSaving(false); }
  }
  async function confirm() {
    if (!selected) return;
    try { const data = await apiRequest<Inspection>(`/inspecciones/${selected.id}/confirmar`, { method: "POST", body: JSON.stringify({ confirmar: true }) }); setSelected(data); await loadInspections(orderId); }
    catch (requestError) { setError(errorText(requestError)); }
  }
  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
    if (!selected || !event.target.files?.[0]) return;
    const body = new FormData(); body.append("archivo", event.target.files[0]); setSaving(true);
    try { await apiRequest<FileData>(`/inspecciones/${selected.id}/archivos`, { method: "POST", body }); await loadInspections(orderId); }
    catch (requestError) { setError(errorText(requestError)); }
    finally { setSaving(false); event.target.value = ""; }
  }

  return <div className="space-y-5">
    <PageHeading title="Inspecciones y evidencias" subtitle="Documenta el estado del vehículo durante la recepción, diagnóstico y entrega." action={<button disabled={!orderId} className="button primary" onClick={openNew}><Plus size={16} /> Nueva inspección</button>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    <select className="form-control max-w-xl" value={orderId} onChange={(event) => { setOrderId(event.target.value); void loadInspections(event.target.value); }}><option value="">Seleccionar orden</option>{orders.map((order) => <option key={order.id} value={order.id}>OT-{String(order.numero).padStart(5, "0")} · {order.vehiculo_placa} · {order.cliente_nombre}</option>)}</select>
    <div className="grid gap-4 xl:grid-cols-[0.7fr_1.3fr]"><section className="space-y-3">{inspections.length === 0 ? <Empty text="Esta orden aún no tiene inspecciones." /> : inspections.map((inspection) => <button key={inspection.id} onClick={() => setSelected(inspection)} className={`w-full rounded-xl border bg-white p-4 text-left shadow-sm ${selected?.id === inspection.id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"}`}><div className="flex justify-between"><strong className="capitalize">{inspection.tipo}</strong>{inspection.confirmada_at ? <span className="text-xs font-bold text-emerald-600">Confirmada</span> : <span className="text-xs font-bold text-orange-600">Borrador</span>}</div><div className="mt-2 text-xs text-slate-500">{new Date(inspection.created_at).toLocaleString("es-PE")} · {inspection.archivos.length} foto(s)</div></button>)}</section>
      <section className="rounded-2xl border bg-white p-5 shadow-sm">{!selected ? <div className="flex min-h-96 items-center justify-center text-sm text-slate-500"><ClipboardCheck className="mr-2 text-blue-600" />Selecciona una inspección</div> : <><div className="flex flex-wrap justify-between gap-3 border-b pb-4"><div><h2 className="text-xl font-bold capitalize">Inspección de {selected.tipo}</h2><p className="text-sm text-slate-500">{selected.kilometraje?.toLocaleString("es-PE") || "—"} km · combustible {selected.nivel_combustible ?? "—"}%</p></div>{selected.confirmada_at ? <span className="flex items-center gap-1 text-sm font-bold text-emerald-600"><CheckCircle2 size={17} /> Confirmada</span> : <button className="button primary" onClick={() => void confirm()}>Confirmar inspección</button>}</div><div className="mt-5 grid gap-2 sm:grid-cols-2">{selected.items.map((item) => <div key={item.codigo} className="rounded-xl bg-slate-50 p-3"><div className="flex justify-between"><strong className="text-sm">{item.nombre}</strong><span className={`text-xs font-bold uppercase ${item.estado === "malo" ? "text-red-600" : item.estado === "regular" ? "text-orange-600" : "text-emerald-600"}`}>{item.estado.replace("_", " ")}</span></div>{item.observacion ? <p className="mt-1 text-xs text-slate-500">{item.observacion}</p> : null}</div>)}</div>{selected.observaciones ? <p className="mt-4 rounded-xl bg-blue-50 p-4 text-sm">{selected.observaciones}</p> : null}<div className="mt-5 border-t pt-5"><div className="mb-3 flex items-center justify-between"><h3 className="flex items-center gap-2 text-sm font-semibold"><Camera size={16} /> Evidencias fotográficas</h3><label className="button cursor-pointer"><Upload size={15} />{saving ? "Subiendo…" : "Subir foto"}<input hidden type="file" accept="image/jpeg,image/png,image/webp" disabled={saving} onChange={(event) => void upload(event)} /></label></div><div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{selected.archivos.length === 0 ? <p className="col-span-full text-sm text-slate-500">No hay fotografías.</p> : selected.archivos.map((file) => file.url ? <a key={file.id} href={file.url} target="_blank" rel="noreferrer" className="overflow-hidden rounded-xl border"><Image loader={({ src }) => src} unoptimized src={file.url} alt={file.nombre_original} width={240} height={160} className="h-32 w-full object-cover" /><div className="truncate p-2 text-xs">{file.nombre_original}</div></a> : <div key={file.id} className="rounded-xl border p-3 text-xs">{file.nombre_original}</div>)}</div></div></>}</section></div>
    {modal ? <Modal title="Nueva inspección" close={() => setModal(false)}><form className="space-y-4" onSubmit={create}><div className="grid gap-3 sm:grid-cols-3"><Field label="Etapa"><select className="form-control" value={type} onChange={(event) => setType(event.target.value)}><option value="recepcion">Recepción</option><option value="diagnostico">Diagnóstico</option><option value="entrega">Entrega</option></select></Field><Field label="Kilometraje"><input type="number" min="0" className="form-control" value={mileage} onChange={(event) => setMileage(event.target.value)} /></Field><Field label={`Combustible (${fuel}%)`}><input type="range" min="0" max="100" step="5" className="h-11 w-full" value={fuel} onChange={(event) => setFuel(event.target.value)} /></Field></div><div className="space-y-2">{items.map((item, index) => <div key={item.codigo} className="grid gap-2 rounded-xl bg-slate-50 p-3 sm:grid-cols-[1fr_140px]"><div><strong className="text-sm">{item.nombre}</strong><input className="mt-2 w-full border-b bg-transparent py-1 text-xs outline-none" placeholder="Observación opcional" value={item.observacion} onChange={(event) => updateItem(index, { observacion: event.target.value })} /></div><select className="form-control" value={item.estado} onChange={(event) => updateItem(index, { estado: event.target.value })}><option value="bueno">Bueno</option><option value="regular">Regular</option><option value="malo">Malo</option><option value="no_aplica">No aplica</option></select></div>)}</div><Field label="Observaciones generales"><textarea className="form-control min-h-20" value={notes} onChange={(event) => setNotes(event.target.value)} /></Field><div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={() => setModal(false)}>Cancelar</button><button disabled={saving} className="button primary">{saving ? "Guardando…" : "Guardar inspección"}</button></div></form></Modal> : null}
  </div>;
}

function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><div className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex justify-between border-b bg-white px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
