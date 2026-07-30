"use client";

import { Check, FileText, Pencil, Plus, Send, Trash2, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiError, apiRequest } from "@/lib/api";
import type { OrdenTrabajo } from "@/types";

type ItemClass = "servicio" | "inventario" | "cliente" | "proveedor";
type Item = { clase: ItemClass; descripcion: string; cantidad: string; precio_unitario: string; descuento: string; producto_id: string; servicio_id: string; proveedor_nombre: string; referencia_externa: string };
type ProductOption = { id: string; sku: string; nombre: string; precio_venta: string; stock_disponible: string; unidad_medida: string };
type ServiceOption = { id: string; codigo: string; nombre: string; categoria: string | null; precio_referencia: string; duracion_minutos: number | null };
type QuoteItem = { id: string; tipo: string; producto_id: string | null; servicio_id: string | null; descripcion: string; cantidad: string; precio_unitario: string; descuento: string; total: string; origen: string | null; proveedor_nombre: string | null; referencia_externa: string | null; recibido_at: string | null; reserva_id: string | null; reserva_estado: string | null };
type Quote = { id: string; orden_id: string; numero: number; version: number; estado: string; subtotal: string; descuento: string; impuesto: string; total: string; valida_hasta: string | null; observaciones: string | null; orden_numero: number; cliente_nombre: string; vehiculo_placa: string; items: QuoteItem[] };

const labels: Record<string, string> = { borrador: "Borrador", enviada: "Enviada", aprobada: "Aprobada", rechazada: "Rechazada", vencida: "Vencida" };
const emptyItem = (clase: ItemClass = "servicio"): Item => ({ clase, descripcion: "", cantidad: "1", precio_unitario: "0", descuento: "0", producto_id: "", servicio_id: "", proveedor_nombre: "", referencia_externa: "" });
const money = (value: string | number) => `S/ ${Number(value).toFixed(2)}`;
const errorMessage = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";

export function CotizacionesModule() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [orders, setOrders] = useState<OrdenTrabajo[]>([]);
  const [products, setProducts] = useState<ProductOption[]>([]);
  const [services, setServices] = useState<ServiceOption[]>([]);
  const [selected, setSelected] = useState<Quote | null>(null);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [orderId, setOrderId] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [discount, setDiscount] = useState("0");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<Item[]>([emptyItem()]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [quoteData, orderData] = await Promise.all([
        apiRequest<Quote[]>("/cotizaciones"),
        apiRequest<OrdenTrabajo[]>("/ordenes?limit=100"),
      ]);
      setQuotes(quoteData);
      setOrders(orderData.filter((order) => !["entregada", "cancelada"].includes(order.estado)));
      setSelected((current) => current ? quoteData.find((quote) => quote.id === current.id) || null : null);
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  const subtotal = useMemo(() => items.reduce((sum, item) => sum + Math.max(0, Number(item.cantidad) * Number(item.precio_unitario) - Number(item.descuento)), 0), [items]);
  const hasService = items.some((item) => item.clase === "servicio" && item.servicio_id);
  const taxable = Math.max(0, subtotal - Number(discount));
  const tax = taxable * 0.18;

  async function selectOrder(id: string) {
    setOrderId(id); setItems([emptyItem()]);
    if (!id) { setProducts([]); setServices([]); return; }
    try { const options = await apiRequest<{ productos: ProductOption[]; servicios: ServiceOption[] }>(`/cotizaciones/opciones/${id}`); setProducts(options.productos); setServices(options.servicios); }
    catch (requestError) { setError(errorMessage(requestError)); }
  }
  function updateItem(index: number, patch: Partial<Item>) { setItems((current) => current.map((item, position) => position === index ? { ...item, ...patch } : item)); }
  function chooseProduct(index: number, id: string) { const product = products.find((value) => value.id === id); updateItem(index, { producto_id: id, descripcion: product?.nombre || "", precio_unitario: product?.precio_venta || "0" }); }
  function chooseService(index: number, id: string) { const service = services.find((value) => value.id === id); updateItem(index, { servicio_id: id, descripcion: service?.nombre || "", precio_unitario: service?.precio_referencia || "0" }); }
  function openNew() { setEditing(null); setOrderId(""); setProducts([]); setServices([]); setValidUntil(""); setDiscount("0"); setNotes(""); setItems([emptyItem()]); setModal(true); }
  async function openEdit(quote: Quote) {
    setEditing(quote); setOrderId(quote.orden_id); setValidUntil(quote.valida_hasta || ""); setDiscount(quote.descuento); setNotes(quote.observaciones || "");
    try {
      const options = await apiRequest<{ productos: ProductOption[]; servicios: ServiceOption[] }>(`/cotizaciones/opciones/${quote.orden_id}`);
      setProducts(options.productos); setServices(options.servicios);
      setItems(quote.items.map((item) => ({ clase: item.tipo === "servicio" ? "servicio" : item.origen === "inventario" ? "inventario" : item.origen === "cliente" ? "cliente" : item.origen === "proveedor" ? "proveedor" : "proveedor", descripcion: item.descripcion, cantidad: item.cantidad, precio_unitario: item.precio_unitario, descuento: item.descuento, producto_id: item.producto_id || "", servicio_id: item.servicio_id || "", proveedor_nombre: item.proveedor_nombre || "", referencia_externa: item.referencia_externa || "" })));
      setModal(true);
    } catch (requestError) { setError(errorMessage(requestError)); }
  }

  async function create(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const quote = await apiRequest<Quote>(editing ? `/cotizaciones/${editing.id}` : "/cotizaciones", { method: editing ? "PATCH" : "POST", body: JSON.stringify({
        orden_id: orderId, valida_hasta: validUntil || null, descuento: Number(discount), observaciones: notes || null,
        items: items.map((item) => ({ ...item, cantidad: Number(item.cantidad), precio_unitario: Number(item.precio_unitario), descuento: Number(item.descuento), producto_id: item.producto_id || null, servicio_id: item.servicio_id || null, proveedor_nombre: item.proveedor_nombre || null, referencia_externa: item.referencia_externa || null, responsable_garantia: item.clase === "cliente" ? "cliente" : item.clase === "proveedor" ? "proveedor" : item.clase === "inventario" ? "taller" : null })),
      }) });
      setModal(false); await load(); setSelected(quote);
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setSaving(false); }
  }
  async function changeStatus(state: "enviada" | "aprobada" | "rechazada") {
    if (!selected) return; setSaving(true);
    try { const quote = await apiRequest<Quote>(`/cotizaciones/${selected.id}/estado`, { method: "PATCH", body: JSON.stringify({ estado: state }) }); setSelected(quote); await load(); }
    catch (requestError) { setError(errorMessage(requestError)); } finally { setSaving(false); }
  }
  async function receiveItem(itemId: string) {
    if (!selected) return;
    try { await apiRequest<void>(`/cotizaciones/${selected.id}/items/${itemId}/recibir`, { method: "POST" }); await load(); }
    catch (requestError) { setError(errorMessage(requestError)); }
  }
  async function consumeItem(reservationId: string) {
    if (!window.confirm("¿Confirmas que el repuesto fue utilizado en la OT?")) return;
    try { await apiRequest<void>(`/cotizaciones/reservas/${reservationId}/consumir`, { method: "POST" }); await load(); }
    catch (requestError) { setError(errorMessage(requestError)); }
  }

  return <div className="space-y-5">
    <PageHeading title="Cotizaciones" subtitle="Servicios, productos propios y repuestos externos." action={<button className="button primary" onClick={openNew}><Plus size={16} /> Nueva cotización</button>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    <div className="grid min-h-[570px] gap-4 xl:grid-cols-[0.85fr_1.2fr]">
      <section className="space-y-3">{loading ? <Empty text="Cargando cotizaciones…" /> : quotes.length === 0 ? <Empty text="Aún no hay cotizaciones." /> : quotes.map((quote) => <button key={quote.id} onClick={() => setSelected(quote)} className={`w-full rounded-xl border bg-white p-4 text-left shadow-sm ${selected?.id === quote.id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"}`}><div className="flex justify-between gap-2"><span className="font-mono text-xs font-bold">COT-{String(quote.numero).padStart(5, "0")} · v{quote.version}</span><StatusBadge status={quote.estado} label={labels[quote.estado]} /></div><div className="mt-3 font-semibold">{quote.cliente_nombre}</div><div className="mt-1 text-xs text-slate-500">OT-{String(quote.orden_numero).padStart(5, "0")} · {quote.vehiculo_placa}</div><div className="mt-3 text-lg font-bold text-blue-700">{money(quote.total)}</div></button>)}</section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">{!selected ? <div className="flex h-full min-h-96 flex-col items-center justify-center"><FileText className="mb-3 text-blue-600" /><h2 className="font-semibold">Selecciona una cotización</h2></div> : <>
        <div className="flex justify-between gap-3 border-b pb-5"><div><h2 className="text-xl font-bold">COT-{String(selected.numero).padStart(5, "0")} <span className="text-sm text-slate-400">v{selected.version}</span></h2><p className="mt-1 text-sm text-slate-500">{selected.cliente_nombre} · {selected.vehiculo_placa}</p></div><div className="flex items-center gap-2">{selected.estado === "borrador" ? <button className="button" onClick={() => void openEdit(selected)}><Pencil size={15} /> Editar</button> : null}<StatusBadge status={selected.estado} label={labels[selected.estado]} /></div></div>
        <div className="mt-5 overflow-hidden rounded-xl border"><div className="grid grid-cols-[1fr_70px_100px] bg-slate-50 px-4 py-2 text-[10px] font-bold uppercase text-slate-400"><span>Descripción</span><span>Cant.</span><span className="text-right">Total</span></div>{selected.items.map((item) => <div key={item.id} className="grid grid-cols-[1fr_70px_100px] border-t px-4 py-3 text-sm"><span>{item.descripcion}<span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-[9px] font-bold uppercase text-slate-500">{item.origen || "servicio"}</span>{["cliente", "proveedor"].includes(item.origen || "") && !item.recibido_at ? <button className="ml-2 text-[10px] font-bold text-blue-600" onClick={() => void receiveItem(item.id)}>Marcar recibido</button> : item.recibido_at ? <span className="ml-2 text-[10px] font-bold text-emerald-600">Recibido</span> : null}{item.reserva_estado === "activa" && item.reserva_id ? <button className="ml-2 text-[10px] font-bold text-orange-600" onClick={() => void consumeItem(item.reserva_id!)}>Registrar uso</button> : item.reserva_estado === "consumida" ? <span className="ml-2 text-[10px] font-bold text-emerald-600">Consumido</span> : null}</span><span>{Number(item.cantidad)}</span><span className="text-right font-semibold">{money(item.total)}</span></div>)}</div>
        <div className="ml-auto mt-5 max-w-xs space-y-2 text-sm"><Line label="Subtotal" value={money(selected.subtotal)} /><Line label="Descuento" value={`- ${money(selected.descuento)}`} /><Line label="IGV" value={money(selected.impuesto)} /><div className="flex justify-between border-t pt-3 text-lg font-bold text-blue-700"><span>Total</span><span>{money(selected.total)}</span></div></div>
        <div className="mt-5 flex justify-end gap-2 border-t pt-5">{selected.estado === "borrador" ? <button disabled={saving} className="button primary" onClick={() => void changeStatus("enviada")}><Send size={15} /> Marcar enviada</button> : null}{selected.estado === "enviada" ? <><button className="button text-red-600" onClick={() => void changeStatus("rechazada")}>Rechazar</button><button className="button primary" onClick={() => void changeStatus("aprobada")}><Check size={15} /> Aprobar y reservar</button></> : null}</div>
      </>}</section>
    </div>
    {modal ? <Modal title={editing ? "Editar cotización" : "Nueva cotización"} close={() => setModal(false)}><form onSubmit={create} className="space-y-4">
      <Field label="Orden de trabajo"><select required disabled={Boolean(editing)} className="form-control" value={orderId} onChange={(event) => void selectOrder(event.target.value)}><option value="">Seleccionar orden</option>{orders.map((order) => <option key={order.id} value={order.id}>OT-{String(order.numero).padStart(5, "0")} · {order.cliente_nombre} · {order.vehiculo_placa}</option>)}</select></Field>
      <div className="grid gap-3 sm:grid-cols-2"><Field label="Válida hasta"><input type="date" className="form-control" value={validUntil} onChange={(event) => setValidUntil(event.target.value)} /></Field><Field label="Descuento general"><input type="number" min="0" step="0.01" className="form-control" value={discount} onChange={(event) => setDiscount(event.target.value)} /></Field></div>
      <div><div className="mb-2 flex justify-between"><h3 className="text-sm font-semibold">Conceptos</h3><button type="button" className="button" onClick={() => setItems([...items, emptyItem()])}><Plus size={14} /> Agregar</button></div><div className="space-y-3">{items.map((item, index) => <div key={index} className="rounded-xl bg-slate-50 p-3">
        <div className="grid gap-2 sm:grid-cols-[170px_1fr_42px]"><select className="form-control" value={item.clase} onChange={(event) => updateItem(index, emptyItem(event.target.value as ItemClass))}><option value="servicio">Servicio / mano de obra</option><option value="inventario">Producto del taller</option><option value="cliente">Repuesto del cliente</option><option value="proveedor">Compra a proveedor</option></select>{item.clase === "servicio" ? <select required className="form-control" value={item.servicio_id} onChange={(event) => chooseService(index, event.target.value)}><option value="">Seleccionar servicio del catálogo</option>{services.map((service) => <option key={service.id} value={service.id}>{service.codigo} · {service.nombre} · S/ {Number(service.precio_referencia).toFixed(2)}{service.duracion_minutos ? ` · ${service.duracion_minutos} min` : ""}</option>)}</select> : item.clase === "inventario" ? <select required className="form-control" value={item.producto_id} onChange={(event) => chooseProduct(index, event.target.value)}><option value="">Seleccionar producto</option>{products.map((product) => <option key={product.id} value={product.id} disabled={Number(product.stock_disponible) <= 0}>{product.sku} · {product.nombre} · disponible {Number(product.stock_disponible)} {product.unidad_medida}</option>)}</select> : <input required className="form-control" placeholder="Descripción" value={item.descripcion} onChange={(event) => updateItem(index, { descripcion: event.target.value })} />}<button type="button" disabled={items.length === 1} className="grid place-items-center text-red-500" onClick={() => setItems(items.filter((_, position) => position !== index))}><Trash2 size={16} /></button></div>
        <div className="mt-2 grid gap-2 sm:grid-cols-3"><Field label="Cantidad"><input required type="number" min="0.01" step="0.01" className="form-control" value={item.cantidad} onChange={(event) => updateItem(index, { cantidad: event.target.value })} /></Field><Field label="Precio unitario"><input required disabled={["servicio", "cliente", "inventario"].includes(item.clase)} type="number" min="0" step="0.01" className="form-control" value={item.precio_unitario} onChange={(event) => updateItem(index, { precio_unitario: event.target.value })} /></Field>{item.clase === "proveedor" ? <Field label="Proveedor"><input required className="form-control" value={item.proveedor_nombre} onChange={(event) => updateItem(index, { proveedor_nombre: event.target.value })} /></Field> : <Field label="Descuento"><input disabled={item.clase === "cliente"} type="number" min="0" step="0.01" className="form-control" value={item.descuento} onChange={(event) => updateItem(index, { descuento: event.target.value })} /></Field>}</div>
        {["cliente", "proveedor"].includes(item.clase) ? <input className="form-control mt-2" placeholder="Referencia o comprobante (opcional)" value={item.referencia_externa} onChange={(event) => updateItem(index, { referencia_externa: event.target.value })} /> : null}
      </div>)}</div></div>
      <Field label="Observaciones"><textarea className="form-control min-h-20" value={notes} onChange={(event) => setNotes(event.target.value)} /></Field>
      {!hasService ? <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">Selecciona al menos un servicio de mano de obra.</div> : null}
      <div className="rounded-xl bg-blue-50 p-4 text-sm"><Line label="Subtotal" value={money(subtotal)} /><Line label="IGV estimado" value={money(tax)} /><div className="mt-2 flex justify-between text-lg font-bold text-blue-700"><span>Total</span><span>{money(taxable + tax)}</span></div></div>
      <div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={() => setModal(false)}>Cancelar</button><button disabled={saving || !hasService} className="button primary">{saving ? "Guardando…" : editing ? "Guardar cambios" : "Crear cotización"}</button></div>
    </form></Modal> : null}
  </div>;
}

function Line({ label, value }: { label: string; value: string }) { return <div className="flex justify-between text-slate-600"><span>{label}</span><span>{value}</span></div>; }
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><div className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex justify-between border-b bg-white px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
