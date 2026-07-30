"use client";

import { ArrowLeftRight, Check, PackageCheck, Plus, Send, Trash2, Truck, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiError, apiRequest } from "@/lib/api";

type Branch = { id: string; nombre: string; es_principal: boolean };
type Product = { id: string; sku: string; nombre: string; stock_actual: string; unidad_medida: string };
type Item = { producto_id: string; cantidad: string; observaciones: string };
type TransferItem = { id: string; producto_id: string; producto_sku: string; producto_nombre: string; unidad_medida: string; cantidad_solicitada: string; cantidad_despachada: string | null; cantidad_recibida: string | null };
type Transfer = { id: string; estado: string; sucursal_origen_id: string; sucursal_origen_nombre: string; sucursal_destino_id: string; sucursal_destino_nombre: string; fecha_solicitud: string; fecha_aprobacion: string | null; fecha_despacho: string | null; fecha_recepcion: string | null; observaciones: string | null; items: TransferItem[] };
const labels: Record<string, string> = { solicitada: "Solicitada", aprobada: "Aprobada", en_transito: "En tránsito", recibida: "Recibida", rechazada: "Rechazada", cancelada: "Cancelada" };
const emptyItem = (): Item => ({ producto_id: "", cantidad: "1", observaciones: "" });
const message = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";

export function TransferenciasModule() {
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selected, setSelected] = useState<Transfer | null>(null);
  const [modal, setModal] = useState(false);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<Item[]>([emptyItem()]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [transferData, branchData] = await Promise.all([
        apiRequest<Transfer[]>("/transferencias"),
        apiRequest<Branch[]>("/transferencias/opciones"),
      ]);
      setTransfers(transferData); setBranches(branchData);
      setSelected((current) => current ? transferData.find((transfer) => transfer.id === current.id) || null : null);
    } catch (requestError) { setError(message(requestError)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  async function chooseOrigin(id: string) {
    setOrigin(id); setItems([emptyItem()]);
    if (!id) return setProducts([]);
    try { setProducts(await apiRequest<Product[]>(`/transferencias/productos-origen/${id}`)); }
    catch (requestError) { setError(message(requestError)); }
  }
  function openNew() { setOrigin(""); setDestination(""); setProducts([]); setNotes(""); setItems([emptyItem()]); setModal(true); }
  function updateItem(index: number, patch: Partial<Item>) { setItems((current) => current.map((item, position) => position === index ? { ...item, ...patch } : item)); }
  async function create(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const transfer = await apiRequest<Transfer>("/transferencias", { method: "POST", body: JSON.stringify({ sucursal_origen_id: origin, sucursal_destino_id: destination, observaciones: notes || null, items: items.map((item) => ({ producto_id: item.producto_id, cantidad: Number(item.cantidad), observaciones: item.observaciones || null })) }) });
      setModal(false); await load(); setSelected(transfer);
    } catch (requestError) { setError(message(requestError)); }
    finally { setSaving(false); }
  }
  async function changeState(state: string) {
    if (!selected) return; setSaving(true);
    try {
      const transfer = await apiRequest<Transfer>(`/transferencias/${selected.id}/estado`, { method: "PATCH", body: JSON.stringify({ estado: state }) });
      setSelected(transfer); await load();
    } catch (requestError) { setError(message(requestError)); }
    finally { setSaving(false); }
  }

  return <div className="space-y-5">
    <PageHeading title="Transferencias" subtitle="Movimientos internos de productos entre sucursales." action={<button className="button primary" disabled={branches.length < 2} onClick={openNew}><Plus size={16} /> Nueva solicitud</button>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    {branches.length < 2 && !loading ? <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">Necesitas al menos dos sucursales activas para realizar transferencias.</div> : null}
    <div className="grid min-h-[570px] gap-4 xl:grid-cols-[0.85fr_1.2fr]">
      <section className="space-y-3">{loading ? <Empty text="Cargando transferencias…" /> : transfers.length === 0 ? <Empty text="Aún no hay transferencias." /> : transfers.map((transfer) => <button key={transfer.id} onClick={() => setSelected(transfer)} className={`w-full rounded-xl border bg-white p-4 text-left shadow-sm ${selected?.id === transfer.id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"}`}><div className="flex justify-between"><span className="font-mono text-xs font-bold">TR-{transfer.id.slice(0, 8).toUpperCase()}</span><StatusBadge status={transfer.estado} label={labels[transfer.estado]} /></div><div className="mt-4 flex items-center gap-2 text-sm font-semibold"><span>{transfer.sucursal_origen_nombre}</span><ArrowLeftRight size={15} className="text-blue-600" /><span>{transfer.sucursal_destino_nombre}</span></div><div className="mt-2 text-xs text-slate-500">{transfer.items.length} producto(s) · {new Date(transfer.fecha_solicitud).toLocaleString("es-PE")}</div></button>)}</section>
      <section className="rounded-2xl border bg-white p-5 shadow-sm">{!selected ? <div className="flex h-full min-h-96 flex-col items-center justify-center"><ArrowLeftRight className="mb-3 text-blue-600" /><h2 className="font-semibold">Selecciona una transferencia</h2></div> : <>
        <div className="flex justify-between gap-3 border-b pb-5"><div><h2 className="text-xl font-bold">TR-{selected.id.slice(0, 8).toUpperCase()}</h2><p className="mt-1 text-sm text-slate-500">{selected.sucursal_origen_nombre} → {selected.sucursal_destino_nombre}</p></div><StatusBadge status={selected.estado} label={labels[selected.estado]} /></div>
        <div className="mt-5 overflow-hidden rounded-xl border"><div className="grid grid-cols-[1fr_90px_90px] bg-slate-50 px-4 py-2 text-[10px] font-bold uppercase text-slate-400"><span>Producto</span><span>Solicitado</span><span>Recibido</span></div>{selected.items.map((item) => <div key={item.id} className="grid grid-cols-[1fr_90px_90px] border-t px-4 py-3 text-sm"><span><strong>{item.producto_nombre}</strong><span className="block text-xs text-slate-500">{item.producto_sku}</span></span><span>{Number(item.cantidad_solicitada)} {item.unidad_medida}</span><span>{item.cantidad_recibida === null ? "—" : Number(item.cantidad_recibida)}</span></div>)}</div>
        {selected.observaciones ? <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{selected.observaciones}</div> : null}
        <div className="mt-5 flex flex-wrap justify-end gap-2 border-t pt-5">{selected.estado === "solicitada" ? <><button disabled={saving} className="button text-red-600" onClick={() => void changeState("rechazada")}>Rechazar</button><button disabled={saving} className="button primary" onClick={() => void changeState("aprobada")}><Check size={15} /> Aprobar</button></> : null}{selected.estado === "aprobada" ? <><button disabled={saving} className="button text-red-600" onClick={() => void changeState("cancelada")}>Cancelar</button><button disabled={saving} className="button primary" onClick={() => void changeState("en_transito")}><Truck size={15} /> Despachar</button></> : null}{selected.estado === "en_transito" ? <button disabled={saving} className="button primary" onClick={() => void changeState("recibida")}><PackageCheck size={15} /> Confirmar recepción</button> : null}</div>
      </>}</section>
    </div>
    {modal ? <Modal close={() => setModal(false)}><form className="space-y-4" onSubmit={create}>
      <div className="grid gap-3 sm:grid-cols-2"><Field label="Sucursal de origen"><select required className="form-control" value={origin} onChange={(event) => void chooseOrigin(event.target.value)}><option value="">Seleccionar</option>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.nombre}</option>)}</select></Field><Field label="Sucursal de destino"><select required className="form-control" value={destination} onChange={(event) => setDestination(event.target.value)}><option value="">Seleccionar</option>{branches.filter((branch) => branch.id !== origin).map((branch) => <option key={branch.id} value={branch.id}>{branch.nombre}</option>)}</select></Field></div>
      <div><div className="mb-2 flex justify-between"><h3 className="text-sm font-semibold">Productos solicitados</h3><button type="button" className="button" disabled={!origin} onClick={() => setItems([...items, emptyItem()])}><Plus size={14} /> Agregar</button></div><div className="space-y-2">{items.map((item, index) => <div key={index} className="grid gap-2 rounded-xl bg-slate-50 p-3 sm:grid-cols-[1fr_100px_42px]"><select required className="form-control" value={item.producto_id} onChange={(event) => updateItem(index, { producto_id: event.target.value })}><option value="">Seleccionar producto</option>{products.filter((product) => !items.some((used, position) => position !== index && used.producto_id === product.id)).map((product) => <option key={product.id} value={product.id}>{product.sku} · {product.nombre} · stock {Number(product.stock_actual)}</option>)}</select><input required type="number" min="0.01" step="0.01" className="form-control" value={item.cantidad} onChange={(event) => updateItem(index, { cantidad: event.target.value })} /><button type="button" disabled={items.length === 1} className="grid place-items-center text-red-500" onClick={() => setItems(items.filter((_, position) => position !== index))}><Trash2 size={16} /></button></div>)}</div></div>
      <Field label="Observaciones"><textarea className="form-control min-h-20" value={notes} onChange={(event) => setNotes(event.target.value)} /></Field>
      <div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={() => setModal(false)}>Cancelar</button><button disabled={saving} className="button primary"><Send size={15} /> {saving ? "Guardando…" : "Crear solicitud"}</button></div>
    </form></Modal> : null}
  </div>;
}
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ close, children }: { close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex justify-between border-b bg-white px-6 py-4"><h2 className="text-lg font-bold">Nueva transferencia</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
