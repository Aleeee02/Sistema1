"use client";

import { ChartNoAxesCombined, CircleDollarSign, ClipboardCheck, Clock3, TrendingUp, WalletCards, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";

type Point = { fecha: string; valor: string };
type Category = { nombre: string; cantidad: string; valor: string };
type Stats = { ingresos: string; por_cobrar: string; ordenes_creadas: number; ordenes_cerradas: number; ordenes_activas: number; ticket_promedio: string; ingresos_diarios: Point[]; ordenes_por_estado: Category[]; servicios_principales: Category[]; pagos_por_metodo: Category[] };
const labels: Record<string, string> = { recepcion: "Recepción", diagnostico: "Diagnóstico", esperando_aprobacion: "Esperando aprobación", aprobada: "Aprobada", en_proceso: "En proceso", terminada: "Terminada", entregada: "Entregada", cancelada: "Cancelada", efectivo: "Efectivo", tarjeta: "Tarjeta", transferencia: "Transferencia", yape: "Yape", plin: "Plin", otro: "Otro" };
const money = (value: string | number) => `S/ ${Number(value).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";

export function EstadisticasModule() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async (period: number) => {
    setLoading(true); setError("");
    const end = new Date(); const start = new Date(); start.setDate(end.getDate() - period + 1);
    const format = (date: Date) => date.toISOString().slice(0, 10);
    try { setStats(await apiRequest<Stats>(`/estadisticas?desde=${format(start)}&hasta=${format(end)}`)); }
    catch (requestError) { setError(errorText(requestError)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(days), 0); return () => window.clearTimeout(timer); }, [days, load]);
  const maxIncome = useMemo(() => Math.max(...(stats?.ingresos_diarios.map((point) => Number(point.valor)) || [0]), 1), [stats]);
  const maxService = useMemo(() => Math.max(...(stats?.servicios_principales.map((item) => Number(item.valor)) || [0]), 1), [stats]);

  return <div className="space-y-5">
    <PageHeading title="Estadísticas del taller" subtitle="Desempeño financiero y operativo calculado con los registros reales." action={<select className="form-control max-w-48" value={days} onChange={(event) => setDays(Number(event.target.value))}><option value={30}>Últimos 30 días</option><option value={90}>Últimos 90 días</option><option value={365}>Último año</option></select>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    {loading || !stats ? <Empty text="Calculando estadísticas…" /> : <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"><Metric icon={<CircleDollarSign size={19} />} label="Ingresos del período" value={money(stats.ingresos)} /><Metric icon={<WalletCards size={19} />} label="Saldo por cobrar" value={money(stats.por_cobrar)} /><Metric icon={<TrendingUp size={19} />} label="Ticket promedio" value={money(stats.ticket_promedio)} /><Metric icon={<ClipboardCheck size={19} />} label="OT creadas" value={String(stats.ordenes_creadas)} /><Metric icon={<ClipboardCheck size={19} />} label="OT entregadas" value={String(stats.ordenes_cerradas)} /><Metric icon={<Clock3 size={19} />} label="OT activas actualmente" value={String(stats.ordenes_activas)} /></div>
      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.8fr]"><Card title="Ingresos registrados"><div className="flex h-64 items-end gap-1 border-b border-slate-200 pt-6">{stats.ingresos_diarios.length === 0 ? <EmptyInner text="No hay pagos en este período." /> : stats.ingresos_diarios.map((point) => <div key={point.fecha} className="group relative flex h-full min-w-2 flex-1 items-end"><div className="w-full rounded-t bg-blue-500 transition hover:bg-blue-600" style={{ height: `${Math.max(4, Number(point.valor) / maxIncome * 100)}%` }} /><span className="pointer-events-none absolute bottom-full left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded bg-slate-900 px-2 py-1 text-[10px] text-white group-hover:block">{point.fecha} · {money(point.valor)}</span></div>)}</div></Card><Card title="Órdenes por estado"><div className="space-y-3">{stats.ordenes_por_estado.map((item) => <div key={item.nombre} className="flex items-center justify-between"><span className="text-sm">{labels[item.nombre] || item.nombre}</span><strong className="rounded-full bg-slate-100 px-2.5 py-1 text-xs">{Number(item.cantidad)}</strong></div>)}</div></Card></div>
      <div className="grid gap-4 xl:grid-cols-2"><Card title="Servicios con mayor facturación"><div className="space-y-4">{stats.servicios_principales.length === 0 ? <EmptyInner text="No hay servicios aprobados en el período." /> : stats.servicios_principales.map((item) => <div key={item.nombre}><div className="mb-1 flex justify-between text-sm"><span className="font-semibold">{item.nombre}</span><span>{money(item.valor)}</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-orange-500" style={{ width: `${Number(item.valor) / maxService * 100}%` }} /></div><div className="mt-1 text-[10px] text-slate-400">{Number(item.cantidad)} servicio(s)</div></div>)}</div></Card><Card title="Cobros por método"><div className="space-y-3">{stats.pagos_por_metodo.length === 0 ? <EmptyInner text="No hay cobros confirmados." /> : stats.pagos_por_metodo.map((item) => <div key={item.nombre} className="flex items-center justify-between rounded-xl bg-slate-50 p-3"><div><strong className="text-sm">{labels[item.nombre] || item.nombre}</strong><div className="text-xs text-slate-500">{Number(item.cantidad)} operación(es)</div></div><strong className="text-emerald-700">{money(item.valor)}</strong></div>)}</div></Card></div>
    </>}
  </div>;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm"><span className="rounded-xl bg-blue-50 p-2.5 text-blue-600">{icon}</span><div><div className="text-xl font-bold">{value}</div><div className="text-xs text-slate-500">{label}</div></div></div>; }
function Card({ title, children }: { title: string; children: React.ReactNode }) { return <section className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="mb-4 flex items-center gap-2 font-bold"><ChartNoAxesCombined size={17} className="text-blue-600" />{title}</h2>{children}</section>; }
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function EmptyInner({ text }: { text: string }) { return <div className="flex h-full w-full items-center justify-center text-center text-sm text-slate-500">{text}</div>; }
