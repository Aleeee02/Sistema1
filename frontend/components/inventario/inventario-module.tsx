"use client";

import { ArrowDownToLine, ArrowUpFromLine, Boxes, PackagePlus, Pencil, Plus, Search, SlidersHorizontal, Trash2, TriangleAlert, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";

type Branch = { id: string; nombre: string; es_principal: boolean };
type Product = { id: string; sku: string; nombre: string; descripcion: string | null; categoria: string | null; unidad_medida: string; costo_promedio: string; precio_venta: string; estado: string; existencia_id: string | null; sucursal_id: string; stock_actual: string; stock_minimo: string; stock_maximo: string | null };
type Movement = { id: string; tipo: string; cantidad: string; costo_unitario: string; stock_anterior: string; stock_resultante: string; motivo: string | null; created_at: string; producto_nombre: string; producto_sku: string };
type ProductForm = { sku: string; nombre: string; descripcion: string; categoria: string; unidad_medida: string; costo_promedio: string; precio_venta: string; stock_minimo: string };
const emptyProduct: ProductForm = { sku: "", nombre: "", descripcion: "", categoria: "", unidad_medida: "unidad", costo_promedio: "0", precio_venta: "0", stock_minimo: "0" };
function message(error: unknown) { return error instanceof ApiError ? error.message : "Ocurrió un error inesperado"; }
function number(value: string) { return Number(value).toLocaleString("es-PE", { maximumFractionDigits: 2 }); }

export function InventarioModule() {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchId, setBranchId] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [movements, setMovements] = useState<Movement[]>([]);
  const [selected, setSelected] = useState<Product | null>(null);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<"stock" | "movimientos">("stock");
  const [productModal, setProductModal] = useState(false);
  const [movementModal, setMovementModal] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [productForm, setProductForm] = useState<ProductForm>(emptyProduct);
  const [movementType, setMovementType] = useState<"entrada" | "salida" | "ajuste">("entrada");
  const [quantity, setQuantity] = useState("");
  const [newStock, setNewStock] = useState("");
  const [unitCost, setUnitCost] = useState("0");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadInventory = useCallback(async (currentBranch: string, term = "") => {
    if (!currentBranch) return;
    setLoading(true);
    try {
      const query = new URLSearchParams({ sucursal_id: currentBranch });
      if (term.trim()) query.set("search", term.trim());
      const [stock, history] = await Promise.all([
        apiRequest<Product[]>(`/inventario?${query}`),
        apiRequest<Movement[]>(`/inventario/movimientos?sucursal_id=${currentBranch}`),
      ]);
      setProducts(stock); setMovements(history);
      setSelected((current) => current ? stock.find((product) => product.id === current.id) || null : null);
    } catch (requestError) { setError(message(requestError)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        const data = await apiRequest<Branch[]>("/sucursales");
        setBranches(data);
        const initial = data[0]?.id || "";
        setBranchId(initial);
        if (initial) await loadInventory(initial);
      } catch (requestError) { setError(message(requestError)); setLoading(false); }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadInventory]);
  useEffect(() => { if (!branchId) return; const timer = window.setTimeout(() => void loadInventory(branchId, search), 300); return () => window.clearTimeout(timer); }, [branchId, search, loadInventory]);

  const lowStock = useMemo(() => products.filter((product) => Number(product.stock_actual) <= Number(product.stock_minimo)).length, [products]);
  const value = useMemo(() => products.reduce((sum, product) => sum + Number(product.stock_actual) * Number(product.costo_promedio), 0), [products]);
  function openNew() { setEditing(null); setProductForm(emptyProduct); setProductModal(true); }
  function openEdit(product: Product) { setEditing(product); setProductForm({ sku: product.sku, nombre: product.nombre, descripcion: product.descripcion || "", categoria: product.categoria || "", unidad_medida: product.unidad_medida, costo_promedio: product.costo_promedio, precio_venta: product.precio_venta, stock_minimo: product.stock_minimo }); setProductModal(true); }
  function openMovement(product: Product, type: "entrada" | "salida" | "ajuste") { setSelected(product); setMovementType(type); setQuantity(""); setNewStock(product.stock_actual); setUnitCost(product.costo_promedio); setReason(""); setMovementModal(true); }
  async function saveProduct(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const payload = { ...productForm, costo_promedio: Number(productForm.costo_promedio), precio_venta: Number(productForm.precio_venta), stock_minimo: Number(productForm.stock_minimo), descripcion: productForm.descripcion || null, categoria: productForm.categoria || null };
      if (editing) await apiRequest<void>(`/inventario/productos/${editing.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      else await apiRequest<Product>(`/inventario/productos?sucursal_id=${branchId}`, { method: "POST", body: JSON.stringify(payload) });
      setProductModal(false); await loadInventory(branchId, search);
    } catch (requestError) { setError(message(requestError)); } finally { setSaving(false); }
  }
  async function saveMovement(event: FormEvent) {
    event.preventDefault(); if (!selected) return; setSaving(true); setError("");
    try {
      await apiRequest<Movement>("/inventario/movimientos", { method: "POST", body: JSON.stringify({ sucursal_id: branchId, producto_id: selected.id, tipo: movementType, cantidad: movementType === "ajuste" ? null : Number(quantity), stock_nuevo: movementType === "ajuste" ? Number(newStock) : null, costo_unitario: Number(unitCost), motivo: reason }) });
      setMovementModal(false); await loadInventory(branchId, search);
    } catch (requestError) { setError(message(requestError)); } finally { setSaving(false); }
  }
  async function deactivate(product: Product) { if (!window.confirm(`¿Desactivar ${product.nombre}?`)) return; try { await apiRequest<void>(`/inventario/productos/${product.id}`, { method: "DELETE" }); setSelected(null); await loadInventory(branchId); } catch (requestError) { setError(message(requestError)); } }

  return <div className="space-y-5">
    <PageHeading title="Inventario" subtitle="Productos y existencias independientes por sucursal." action={<button className="button primary" onClick={openNew} disabled={!branchId}><Plus size={16} /> Nuevo producto</button>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    <div className="grid gap-3 sm:grid-cols-3"><Metric icon={<Boxes size={19} />} label="Productos" value={String(products.length)} /><Metric icon={<TriangleAlert size={19} />} label="Stock bajo" value={String(lowStock)} warn={lowStock > 0} /><Metric icon={<PackagePlus size={19} />} label="Valor a costo" value={`S/ ${value.toFixed(2)}`} /></div>
    <div className="flex flex-col gap-3 rounded-xl border bg-white p-3 sm:flex-row"><select className="form-control sm:max-w-64" value={branchId} onChange={(e) => setBranchId(e.target.value)}>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.nombre}{branch.es_principal ? " · Principal" : ""}</option>)}</select><label className="flex flex-1 items-center gap-2 rounded-lg bg-slate-50 px-3"><Search size={17} className="text-slate-400" /><input className="h-10 w-full bg-transparent text-sm outline-none" placeholder="SKU, producto o categoría" value={search} onChange={(e) => setSearch(e.target.value)} /></label><div className="flex rounded-lg bg-slate-100 p-1"><button className={`rounded-md px-3 text-xs font-semibold ${tab === "stock" ? "bg-white shadow-sm" : ""}`} onClick={() => setTab("stock")}>Existencias</button><button className={`rounded-md px-3 text-xs font-semibold ${tab === "movimientos" ? "bg-white shadow-sm" : ""}`} onClick={() => setTab("movimientos")}>Movimientos</button></div></div>
    {loading ? <Empty text="Cargando inventario…" /> : !branchId ? <Empty text="Primero crea una sucursal." /> : tab === "movimientos" ? <div className="overflow-hidden rounded-xl border bg-white shadow-sm">{movements.length === 0 ? <Empty text="No hay movimientos en esta sucursal." /> : movements.map((movement) => <div key={movement.id} className="grid gap-2 border-b px-4 py-3 text-sm sm:grid-cols-[1fr_120px_150px]"><div><strong>{movement.producto_nombre}</strong><div className="text-xs text-slate-500">{movement.producto_sku} · {movement.motivo}</div></div><span className={movement.tipo === "salida" ? "font-semibold text-red-600" : "font-semibold text-emerald-600"}>{movement.tipo === "salida" ? "-" : "+"}{number(movement.cantidad)}</span><span className="text-xs text-slate-500">{number(movement.stock_anterior)} → {number(movement.stock_resultante)}<br />{new Date(movement.created_at).toLocaleString("es-PE")}</span></div>)}</div> :
    <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr]"><section className="grid content-start gap-3 sm:grid-cols-2 xl:grid-cols-1">{products.length === 0 ? <Empty text="No hay productos registrados." /> : products.map((product) => { const low = Number(product.stock_actual) <= Number(product.stock_minimo); return <button key={product.id} onClick={() => setSelected(product)} className={`rounded-xl border bg-white p-4 text-left shadow-sm ${selected?.id === product.id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"}`}><div className="flex justify-between gap-2"><span className="font-mono text-xs font-bold text-slate-500">{product.sku}</span>{low ? <span className="rounded-full bg-red-50 px-2 py-1 text-[10px] font-bold text-red-700">Stock bajo</span> : <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">Disponible</span>}</div><h3 className="mt-2 font-semibold">{product.nombre}</h3><div className="mt-3 flex items-end justify-between"><span className="text-xs text-slate-500">{product.categoria || "Sin categoría"}</span><span className="text-xl font-bold">{number(product.stock_actual)} <small className="text-xs font-medium text-slate-400">{product.unidad_medida}</small></span></div></button>; })}</section>
      <section className="rounded-2xl border bg-white p-5 shadow-sm">{!selected ? <div className="flex min-h-96 items-center justify-center text-sm text-slate-500">Selecciona un producto</div> : <><div className="flex justify-between border-b pb-5"><div><h2 className="text-xl font-bold">{selected.nombre}</h2><p className="mt-1 font-mono text-xs text-slate-500">{selected.sku}</p></div><div className="flex gap-2"><button className="button" onClick={() => openEdit(selected)}><Pencil size={15} /></button><button className="button text-red-600" onClick={() => void deactivate(selected)}><Trash2 size={15} /></button></div></div><div className="grid gap-3 py-5 sm:grid-cols-2"><Info label="Stock actual" value={`${number(selected.stock_actual)} ${selected.unidad_medida}`} /><Info label="Stock mínimo" value={`${number(selected.stock_minimo)} ${selected.unidad_medida}`} /><Info label="Costo promedio" value={`S/ ${number(selected.costo_promedio)}`} /><Info label="Precio de venta" value={`S/ ${number(selected.precio_venta)}`} /></div><div className="grid gap-2 sm:grid-cols-3"><button className="button primary" onClick={() => openMovement(selected, "entrada")}><ArrowDownToLine size={15} /> Entrada</button><button className="button" onClick={() => openMovement(selected, "salida")}><ArrowUpFromLine size={15} /> Salida</button><button className="button" onClick={() => openMovement(selected, "ajuste")}><SlidersHorizontal size={15} /> Ajuste</button></div></>}</section></div>}
    {productModal ? <Modal title={editing ? "Editar producto" : "Nuevo producto"} close={() => setProductModal(false)}><form className="space-y-4" onSubmit={saveProduct}><div className="grid gap-3 sm:grid-cols-2"><Field label="SKU"><input required className="form-control uppercase" value={productForm.sku} onChange={(e) => setProductForm({ ...productForm, sku: e.target.value })} /></Field><Field label="Nombre"><input required className="form-control" value={productForm.nombre} onChange={(e) => setProductForm({ ...productForm, nombre: e.target.value })} /></Field><Field label="Categoría"><input className="form-control" value={productForm.categoria} onChange={(e) => setProductForm({ ...productForm, categoria: e.target.value })} /></Field><Field label="Unidad"><select className="form-control" value={productForm.unidad_medida} onChange={(e) => setProductForm({ ...productForm, unidad_medida: e.target.value })}><option>unidad</option><option>litro</option><option>galón</option><option>kilogramo</option><option>juego</option></select></Field><Field label="Costo"><input type="number" min="0" step="0.01" className="form-control" value={productForm.costo_promedio} onChange={(e) => setProductForm({ ...productForm, costo_promedio: e.target.value })} /></Field><Field label="Precio venta"><input type="number" min="0" step="0.01" className="form-control" value={productForm.precio_venta} onChange={(e) => setProductForm({ ...productForm, precio_venta: e.target.value })} /></Field>{!editing ? <Field label="Stock mínimo inicial"><input type="number" min="0" step="0.01" className="form-control" value={productForm.stock_minimo} onChange={(e) => setProductForm({ ...productForm, stock_minimo: e.target.value })} /></Field> : null}</div><Field label="Descripción"><textarea className="form-control min-h-20" value={productForm.descripcion} onChange={(e) => setProductForm({ ...productForm, descripcion: e.target.value })} /></Field><Actions saving={saving} cancel={() => setProductModal(false)} label="Guardar producto" /></form></Modal> : null}
    {movementModal && selected ? <Modal title={`${movementType === "entrada" ? "Entrada" : movementType === "salida" ? "Salida" : "Ajuste"} · ${selected.nombre}`} close={() => setMovementModal(false)}><form className="space-y-4" onSubmit={saveMovement}>{movementType === "ajuste" ? <Field label="Nuevo stock"><input required type="number" min="0" step="0.01" className="form-control" value={newStock} onChange={(e) => setNewStock(e.target.value)} /></Field> : <Field label="Cantidad"><input required type="number" min="0.01" step="0.01" className="form-control" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></Field>}{movementType === "entrada" ? <Field label="Costo unitario"><input type="number" min="0" step="0.01" className="form-control" value={unitCost} onChange={(e) => setUnitCost(e.target.value)} /></Field> : null}<Field label="Motivo"><textarea required minLength={2} className="form-control min-h-20" placeholder="Compra, consumo interno, conteo físico…" value={reason} onChange={(e) => setReason(e.target.value)} /></Field><Actions saving={saving} cancel={() => setMovementModal(false)} label="Registrar movimiento" /></form></Modal> : null}
  </div>;
}
function Metric({ icon, label, value, warn = false }: { icon: React.ReactNode; label: string; value: string; warn?: boolean }) { return <div className="flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm"><span className={`rounded-xl p-2.5 ${warn ? "bg-red-50 text-red-600" : "bg-blue-50 text-blue-600"}`}>{icon}</span><div><div className="text-xl font-bold">{value}</div><div className="text-xs text-slate-500">{label}</div></div></div>; }
function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-slate-50 p-3"><div className="text-[10px] font-bold uppercase text-slate-400">{label}</div><div className="mt-1 font-semibold">{value}</div></div>; }
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}><div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex justify-between border-b bg-white px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
function Actions({ saving, cancel, label }: { saving: boolean; cancel: () => void; label: string }) { return <div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={cancel}>Cancelar</button><button disabled={saving} className="button primary">{saving ? "Guardando…" : label}</button></div>; }
