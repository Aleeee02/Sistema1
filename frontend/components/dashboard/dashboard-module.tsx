"use client";

import { CircleDollarSign, ClipboardCheck, Clock3, Package, TriangleAlert, WalletCards, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiError, apiRequest } from "@/lib/api";
import type { OrdenTrabajo } from "@/types";

type Stats = { ingresos: string; por_cobrar: string; ordenes_creadas: number; ordenes_cerradas: number; ordenes_activas: number; ticket_promedio: string; ingresos_diarios: { fecha: string; valor: string }[] };
type Branch = { id: string; nombre: string; es_principal: boolean };
type Stock = { id: string; sku: string; nombre: string; unidad_medida: string; stock_actual: string; stock_minimo: string };
const labels: Record<string, string> = { recepcion: "Recepción", diagnostico: "Diagnóstico", esperando_aprobacion: "Esperando aprobación", aprobada: "Aprobada", en_proceso: "En proceso", terminada: "Terminada", entregada: "Entregada", cancelada: "Cancelada" };
const money = (value: string | number) => `S/ ${Number(value).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";

export function DashboardModule() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [orders, setOrders] = useState<OrdenTrabajo[]>([]);
  const [branch, setBranch] = useState<Branch | null>(null);
  const [stock, setStock] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        const today = new Date(); const start = new Date(today.getFullYear(), today.getMonth(), 1);
        const [statData, orderData, branches] = await Promise.all([
          apiRequest<Stats>(`/estadisticas?desde=${start.toISOString().slice(0, 10)}&hasta=${today.toISOString().slice(0, 10)}`),
          apiRequest<OrdenTrabajo[]>("/ordenes?limit=8"),
          apiRequest<Branch[]>("/sucursales"),
        ]);
        setStats(statData); setOrders(orderData.filter((order) => !["entregada", "cancelada"].includes(order.estado)).slice(0, 5));
        const current = branches[0] || null; setBranch(current);
        if (current) setStock(await apiRequest<Stock[]>(`/inventario?sucursal_id=${current.id}`));
      } catch (requestError) { setError(errorText(requestError)); }
      finally { setLoading(false); }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  const lowStock = stock.filter((item) => Number(item.stock_actual) <= Number(item.stock_minimo)).slice(0, 5);
  const maxIncome = Math.max(...(stats?.ingresos_diarios.map((item) => Number(item.valor)) || [0]), 1);

  return <div className="space-y-5">
    <PageHeading title="Resumen del taller" subtitle="Información real de la empresa y sus operaciones actuales." />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    {loading || !stats ? <Empty text="Cargando resumen…" /> : <>
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric icon={<CircleDollarSign size={18} />} label="Ingresos del mes" value={money(stats.ingresos)} detail={`${stats.ordenes_cerradas} OT entregadas`} /><Metric icon={<WalletCards size={18} />} label="Saldo por cobrar" value={money(stats.por_cobrar)} detail="Cuentas pendientes" /><Metric icon={<ClipboardCheck size={18} />} label="Órdenes activas" value={String(stats.ordenes_activas)} detail={`${stats.ordenes_creadas} creadas este mes`} /><Metric icon={<Clock3 size={18} />} label="Ticket promedio" value={money(stats.ticket_promedio)} detail="Por operación de pago" /></section>
      <div className="grid gap-4 xl:grid-cols-[1.35fr_0.8fr]"><div className="space-y-4"><section className="rounded-2xl border bg-white p-5 shadow-sm"><div className="mb-4 flex items-center justify-between"><h2 className="font-bold">Órdenes activas recientes</h2><Link href="/ordenes" className="text-xs font-bold text-blue-600">Ver todas</Link></div><div className="space-y-2">{orders.length === 0 ? <EmptyInner text="No hay órdenes activas." /> : orders.map((order) => <Link href="/ordenes" key={order.id} className="grid gap-2 rounded-xl bg-slate-50 p-3 sm:grid-cols-[100px_1fr_auto]"><span className="font-mono text-xs font-bold">OT-{String(order.numero).padStart(5, "0")}</span><div><strong className="text-sm">{order.vehiculo_placa} · {order.cliente_nombre}</strong><div className="line-clamp-1 text-xs text-slate-500">{order.falla_reportada || "Sin falla registrada"} · {order.sucursal_nombre}</div></div><StatusBadge status={order.estado} label={labels[order.estado]} /></Link>)}</div></section><section className="rounded-2xl border bg-white p-5 shadow-sm"><div className="mb-4 flex justify-between"><h2 className="font-bold">Ingresos diarios del mes</h2><Link href="/estadisticas" className="text-xs font-bold text-blue-600">Más estadísticas</Link></div><div className="flex h-44 items-end gap-1 border-b">{stats.ingresos_diarios.length === 0 ? <EmptyInner text="Aún no hay ingresos este mes." /> : stats.ingresos_diarios.map((point) => <div key={point.fecha} className="group relative flex h-full min-w-2 flex-1 items-end"><div className="w-full rounded-t bg-blue-500" style={{ height: `${Math.max(5, Number(point.valor) / maxIncome * 100)}%` }} /><span className="absolute bottom-full left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-slate-900 px-2 py-1 text-[10px] text-white group-hover:block">{point.fecha} · {money(point.valor)}</span></div>)}</div></section></div>
        <section className="rounded-2xl border bg-white p-5 shadow-sm"><div className="mb-4 flex justify-between"><div><h2 className="font-bold">Alertas de inventario</h2><p className="text-xs text-slate-500">{branch?.nombre || "Sin sucursal"}</p></div><Link href="/inventario" className="text-xs font-bold text-blue-600">Ir al inventario</Link></div>{lowStock.length === 0 ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">No hay productos con stock bajo.</div> : <div className="space-y-3">{lowStock.map((item) => <div key={item.id} className="flex gap-3 rounded-xl border border-orange-200 bg-orange-50 p-3"><span className="text-orange-600"><TriangleAlert size={17} /></span><div><strong className="text-sm">{item.nombre}</strong><div className="text-xs text-orange-700">{item.sku} · {Number(item.stock_actual)} {item.unidad_medida} disponibles</div><div className="text-[10px] text-slate-500">Mínimo: {Number(item.stock_minimo)}</div></div></div>)}</div>}<div className="mt-5 flex items-center gap-2 border-t pt-4 text-xs text-slate-500"><Package size={15} />{stock.length} productos activos en la sucursal principal</div></section>
      </div>
    </>}
  </div>;
}

function Metric({ icon, label, value, detail }: { icon: React.ReactNode; label: string; value: string; detail: string }) { return <article className="rounded-2xl border bg-white p-5 shadow-sm"><div className="flex justify-between"><span className="text-xs text-slate-500">{label}</span><span className="rounded-xl bg-blue-50 p-2 text-blue-600">{icon}</span></div><div className="mt-2 text-2xl font-bold">{value}</div><div className="mt-1 text-xs text-slate-400">{detail}</div></article>; }
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function EmptyInner({ text }: { text: string }) { return <div className="flex min-h-24 items-center justify-center text-center text-sm text-slate-500">{text}</div>; }
