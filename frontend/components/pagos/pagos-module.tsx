"use client";

import { Banknote, Ban, CheckCircle2, CreditCard, HandCoins, Plus, Search, Settings2, X } from "lucide-react";
import Image from "next/image";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiError, apiRequest } from "@/lib/api";
import { usePermissions } from "@/lib/use-permissions";

type Account = { orden_id: string; orden_numero: number; sucursal_id: string; sucursal_nombre: string; cliente_nombre: string; vehiculo_placa: string; estado: string; total: string; saldo: string };
type Payment = { id: string; sucursal_nombre: string; orden_id: string; orden_numero: number; cliente_nombre: string; vehiculo_placa: string; numero: number; metodo: string; monto: string; moneda: string; referencia: string | null; estado: string; motivo_anulacion: string | null; anulado_at: string | null; created_at: string };
type MethodConfig = { id: string | null; metodo: string; activo: boolean; nombre_mostrar: string; configuracion: Record<string, string> };
const methods: Record<string, string> = { efectivo: "Efectivo", tarjeta: "Tarjeta", transferencia: "Transferencia", yape: "Yape", plin: "Plin", otro: "Otro" };
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";
const money = (value: string | number) => `S/ ${Number(value).toFixed(2)}`;

export function PagosModule() {
  const { can } = usePermissions();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [methodConfigs, setMethodConfigs] = useState<MethodConfig[]>([]);
  const [selected, setSelected] = useState<Account | null>(null);
  const [tab, setTab] = useState<"cuentas" | "historial">("cuentas");
  const [search, setSearch] = useState("");
  const [modal, setModal] = useState(false);
  const [settingsModal, setSettingsModal] = useState(false);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("efectivo");
  const [reference, setReference] = useState("");
  const [cashConfirmed, setCashConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [accountData, paymentData, methodData] = await Promise.all([apiRequest<Account[]>("/pagos/cuentas"), apiRequest<Payment[]>("/pagos"), apiRequest<MethodConfig[]>("/pagos/metodos")]);
      setAccounts(accountData); setPayments(paymentData); setMethodConfigs(methodData);
      setSelected((value) => value ? accountData.find((account) => account.orden_id === value.orden_id) || null : null);
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  const pending = accounts.reduce((sum, account) => sum + Number(account.saldo), 0);
  const collected = payments.filter((payment) => payment.estado === "confirmado").reduce((sum, payment) => sum + Number(payment.monto), 0);
  const filteredAccounts = useMemo(() => {
    const term = search.trim().toLowerCase();
    return !term ? accounts : accounts.filter((account) => `${account.orden_numero} ${account.cliente_nombre} ${account.vehiculo_placa}`.toLowerCase().includes(term));
  }, [accounts, search]);
  const filteredPayments = useMemo(() => {
    const term = search.trim().toLowerCase();
    return !term ? payments : payments.filter((payment) => `${payment.numero} ${payment.orden_numero} ${payment.cliente_nombre} ${payment.vehiculo_placa} ${payment.referencia || ""}`.toLowerCase().includes(term));
  }, [payments, search]);

  const activeMethods = methodConfigs.filter((item) => item.activo);
  const selectedMethod = methodConfigs.find((item) => item.metodo === method);
  function openPayment(account: Account) { setSelected(account); setAmount(account.saldo); setMethod(activeMethods[0]?.metodo || "efectivo"); setReference(""); setCashConfirmed(false); setModal(true); }
  async function pay(event: FormEvent) {
    event.preventDefault(); if (!selected) return; setSaving(true); setError("");
    try {
      await apiRequest<Payment>("/pagos", { method: "POST", body: JSON.stringify({ orden_id: selected.orden_id, metodo: method, monto: Number(amount), referencia: reference || null, efectivo_confirmado: cashConfirmed }) });
      setModal(false); await load();
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setSaving(false); }
  }
  async function cancelPayment(payment: Payment) {
    const reason = window.prompt("Indica el motivo de la anulación:");
    if (!reason || reason.trim().length < 3) return;
    try { await apiRequest<Payment>(`/pagos/${payment.id}/anular`, { method: "POST", body: JSON.stringify({ motivo: reason.trim() }) }); await load(); }
    catch (requestError) { setError(errorText(requestError)); }
  }
  function patchMethod(index: number, patch: Partial<MethodConfig>) { setMethodConfigs((current) => current.map((item, position) => position === index ? { ...item, ...patch } : item)); }
  function patchDetail(index: number, key: string, value: string) { patchMethod(index, { configuracion: { ...methodConfigs[index].configuracion, [key]: value } }); }
  async function saveMethods() {
    setSaving(true); setError("");
    try { setMethodConfigs(await apiRequest<MethodConfig[]>("/pagos/metodos", { method: "PUT", body: JSON.stringify(methodConfigs.map(({ metodo, activo, nombre_mostrar, configuracion }) => ({ metodo, activo, nombre_mostrar, configuracion }))) })); setSettingsModal(false); }
    catch (requestError) { setError(errorText(requestError)); }
    finally { setSaving(false); }
  }

  return <div className="space-y-5">
    <PageHeading title="Pagos y saldos" subtitle="Registra abonos y controla las cuentas pendientes de cada orden." action={<div className="flex gap-2">{can("pagos.configurar") ? <button className="button" onClick={() => setSettingsModal(true)}><Settings2 size={16} /> Métodos</button> : null}{can("pagos.registrar") ? <button className="button primary" disabled={!selected || Number(selected.saldo) <= 0 || activeMethods.length === 0} onClick={() => selected && openPayment(selected)}><Plus size={16} /> Registrar pago</button> : null}</div>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    <div className="grid gap-3 sm:grid-cols-3"><Metric icon={<HandCoins size={19} />} label="Por cobrar" value={money(pending)} /><Metric icon={<CheckCircle2 size={19} />} label="Cobrado confirmado" value={money(collected)} /><Metric icon={<CreditCard size={19} />} label="Pagos registrados" value={String(payments.filter((payment) => payment.estado === "confirmado").length)} /></div>
    <div className="flex flex-col gap-3 rounded-xl border bg-white p-3 shadow-sm sm:flex-row"><div className="flex rounded-lg bg-slate-100 p-1"><button className={`rounded-md px-4 py-2 text-xs font-semibold ${tab === "cuentas" ? "bg-white shadow-sm" : ""}`} onClick={() => setTab("cuentas")}>Cuentas por cobrar</button><button className={`rounded-md px-4 py-2 text-xs font-semibold ${tab === "historial" ? "bg-white shadow-sm" : ""}`} onClick={() => setTab("historial")}>Historial de pagos</button></div><label className="flex flex-1 items-center gap-2 rounded-lg bg-slate-50 px-3"><Search size={17} className="text-slate-400" /><input className="h-10 w-full bg-transparent text-sm outline-none" placeholder="Buscar OT, cliente, placa o referencia" value={search} onChange={(event) => setSearch(event.target.value)} /></label></div>
    {loading ? <Empty text="Cargando información de caja…" /> : tab === "cuentas" ? <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
      <section className="space-y-3">{filteredAccounts.length === 0 ? <Empty text="No hay órdenes con importes aprobados." /> : filteredAccounts.map((account) => { const paid = Number(account.saldo) === 0; return <button key={account.orden_id} onClick={() => setSelected(account)} className={`w-full rounded-xl border bg-white p-4 text-left shadow-sm ${selected?.orden_id === account.orden_id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"}`}><div className="flex justify-between"><span className="font-mono text-xs font-bold">OT-{String(account.orden_numero).padStart(5, "0")}</span><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${paid ? "bg-emerald-50 text-emerald-700" : "bg-orange-50 text-orange-700"}`}>{paid ? "Pagada" : "Pendiente"}</span></div><h3 className="mt-3 font-semibold">{account.cliente_nombre}</h3><p className="text-xs text-slate-500">{account.vehiculo_placa} · {account.sucursal_nombre}</p><div className="mt-4 flex justify-between"><span className="text-sm text-slate-500">Total {money(account.total)}</span><strong className={paid ? "text-emerald-700" : "text-orange-700"}>Saldo {money(account.saldo)}</strong></div></button>; })}</section>
      <section className="rounded-2xl border bg-white p-5 shadow-sm">{!selected ? <div className="flex min-h-80 items-center justify-center text-sm text-slate-500">Selecciona una cuenta</div> : <><div className="border-b pb-5"><span className="font-mono text-xs font-bold text-blue-700">OT-{String(selected.orden_numero).padStart(5, "0")}</span><h2 className="mt-1 text-xl font-bold">{selected.cliente_nombre}</h2><p className="text-sm text-slate-500">{selected.vehiculo_placa} · {selected.sucursal_nombre}</p></div><div className="grid gap-3 py-5 sm:grid-cols-2"><Info label="Total aprobado" value={money(selected.total)} /><Info label="Saldo pendiente" value={money(selected.saldo)} /><Info label="Importe pagado" value={money(Number(selected.total) - Number(selected.saldo))} /><Info label="Estado de la OT" value={selected.estado.replaceAll("_", " ")} /></div>{can("pagos.registrar") ? <button disabled={Number(selected.saldo) <= 0} className="button primary w-full" onClick={() => openPayment(selected)}><Banknote size={16} />{Number(selected.saldo) <= 0 ? "Cuenta pagada" : "Registrar abono"}</button> : null}</>}</section>
    </div> : <div className="overflow-hidden rounded-xl border bg-white shadow-sm">{filteredPayments.length === 0 ? <Empty text="Aún no existen pagos." /> : filteredPayments.map((payment) => <div key={payment.id} className="grid gap-3 border-b p-4 text-sm md:grid-cols-[100px_1fr_130px_130px_auto]"><div><span className="font-mono text-xs font-bold">P-{String(payment.numero).padStart(5, "0")}</span><div className="text-[10px] text-slate-400">OT-{String(payment.orden_numero).padStart(5, "0")}</div></div><div><strong>{payment.cliente_nombre}</strong><div className="text-xs text-slate-500">{payment.vehiculo_placa} · {payment.sucursal_nombre}</div></div><div><strong>{methods[payment.metodo]}</strong><div className="text-xs text-slate-500">{payment.referencia || "Sin referencia"}</div></div><strong className={payment.estado === "anulado" ? "text-slate-400 line-through" : "text-emerald-700"}>{money(payment.monto)}</strong><div className="flex items-center justify-end gap-2"><StatusBadge status={payment.estado} label={payment.estado === "confirmado" ? "Confirmado" : "Anulado"} />{payment.estado === "confirmado" && can("pagos.anular") ? <button className="button text-red-600" onClick={() => void cancelPayment(payment)} title="Anular pago"><Ban size={14} /></button> : null}</div></div>)}</div>}
    {modal && selected ? <Modal title={`Registrar pago · OT-${String(selected.orden_numero).padStart(5, "0")}`} close={() => setModal(false)}><form className="space-y-4" onSubmit={pay}><div className="rounded-xl bg-blue-50 p-4 text-sm"><div className="flex justify-between"><span>Saldo pendiente</span><strong className="text-blue-700">{money(selected.saldo)}</strong></div></div><div className="grid gap-3 sm:grid-cols-2"><Field label="Monto"><input required autoFocus type="number" min="0.01" max={selected.saldo} step="0.01" className="form-control" value={amount} onChange={(event) => setAmount(event.target.value)} /></Field><Field label="Método"><select className="form-control" value={method} onChange={(event) => { setMethod(event.target.value); setCashConfirmed(false); }}><option value="">Seleccionar</option>{activeMethods.map((item) => <option key={item.metodo} value={item.metodo}>{item.nombre_mostrar}</option>)}</select></Field></div>{selectedMethod ? <MethodDetails method={selectedMethod} /> : null}{method === "efectivo" ? <label className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm"><input required type="checkbox" className="mt-1" checked={cashConfirmed} onChange={(event) => setCashConfirmed(event.target.checked)} /><span><strong>Confirmo que recibí el efectivo</strong><br /><span className="text-xs text-amber-700">El pago se registrará inmediatamente en caja.</span></span></label> : <Field label="Código o número de operación"><input required className="form-control" placeholder="Voucher, operación o autorización" value={reference} onChange={(event) => setReference(event.target.value)} /></Field>}<div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={() => setModal(false)}>Cancelar</button><button disabled={saving || !method} className="button primary">{saving ? "Registrando…" : "Confirmar pago"}</button></div></form></Modal> : null}
    {settingsModal ? <Modal title="Configurar métodos de pago" close={() => setSettingsModal(false)}><div className="space-y-3">{methodConfigs.map((item, index) => <div key={item.metodo} className="rounded-xl border p-4"><div className="flex items-center gap-3"><input type="checkbox" checked={item.activo} onChange={(event) => patchMethod(index, { activo: event.target.checked })} /><input className="form-control font-semibold" value={item.nombre_mostrar} onChange={(event) => patchMethod(index, { nombre_mostrar: event.target.value })} /></div>{item.activo && ["yape", "plin"].includes(item.metodo) ? <div className="mt-3 grid gap-2 sm:grid-cols-2"><input className="form-control" placeholder="Número de celular" value={item.configuracion.numero || ""} onChange={(event) => patchDetail(index, "numero", event.target.value)} /><input className="form-control" placeholder="Titular" value={item.configuracion.titular || ""} onChange={(event) => patchDetail(index, "titular", event.target.value)} /><input className="form-control sm:col-span-2" placeholder="URL pública de la imagen QR" value={item.configuracion.qr_url || ""} onChange={(event) => patchDetail(index, "qr_url", event.target.value)} /></div> : null}{item.activo && item.metodo === "transferencia" ? <div className="mt-3 grid gap-2 sm:grid-cols-2"><input className="form-control" placeholder="Banco" value={item.configuracion.banco || ""} onChange={(event) => patchDetail(index, "banco", event.target.value)} /><input className="form-control" placeholder="Titular" value={item.configuracion.titular || ""} onChange={(event) => patchDetail(index, "titular", event.target.value)} /><input className="form-control" placeholder="Número de cuenta" value={item.configuracion.cuenta || ""} onChange={(event) => patchDetail(index, "cuenta", event.target.value)} /><input className="form-control" placeholder="CCI" value={item.configuracion.cci || ""} onChange={(event) => patchDetail(index, "cci", event.target.value)} /></div> : null}{item.activo && item.metodo === "tarjeta" ? <p className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">Modo actual: POS físico. Al cobrar se solicitará el código de autorización del voucher. El pago web requiere integrar una pasarela.</p> : null}</div>)}</div><div className="mt-5 flex justify-end gap-2 border-t pt-4"><button className="button" onClick={() => setSettingsModal(false)}>Cancelar</button><button disabled={saving} className="button primary" onClick={() => void saveMethods()}>{saving ? "Guardando…" : "Guardar configuración"}</button></div></Modal> : null}
  </div>;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm"><span className="rounded-xl bg-blue-50 p-2.5 text-blue-600">{icon}</span><div><div className="text-xl font-bold">{value}</div><div className="text-xs text-slate-500">{label}</div></div></div>; }
function MethodDetails({ method }: { method: MethodConfig }) {
  const config = method.configuracion;
  if (!["yape", "plin", "transferencia"].includes(method.metodo)) return null;
  return <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-4"><div className="text-xs font-bold uppercase tracking-wide text-blue-700">Datos para realizar el pago</div><div className="mt-3 flex gap-4"><div className="grid flex-1 gap-2 text-sm">{config.titular ? <Detail label="Titular" value={config.titular} /> : null}{config.numero ? <Detail label="Número" value={config.numero} /> : null}{config.banco ? <Detail label="Banco" value={config.banco} /> : null}{config.cuenta ? <Detail label="Cuenta" value={config.cuenta} /> : null}{config.cci ? <Detail label="CCI" value={config.cci} /> : null}</div>{config.qr_url ? <a href={config.qr_url} target="_blank" rel="noreferrer" className="shrink-0 rounded-xl border bg-white p-2"><Image loader={({ src }) => src} unoptimized src={config.qr_url} alt={`QR de ${method.nombre_mostrar}`} width={104} height={104} className="size-24 object-contain" /></a> : null}</div></div>;
}
function Detail({ label, value }: { label: string; value: string }) { return <div><span className="text-xs text-slate-500">{label}</span><div className="font-semibold text-slate-900">{value}</div></div>; }
function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-slate-50 p-3"><div className="text-[10px] font-bold uppercase text-slate-400">{label}</div><div className="mt-1 font-semibold capitalize">{value}</div></div>; }
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><div className="w-full max-w-xl rounded-2xl bg-white shadow-2xl"><div className="flex justify-between border-b px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
