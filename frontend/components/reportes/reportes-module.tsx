"use client";

import { Boxes, Download, FileDown, HandCoins, LoaderCircle, Wrench, X } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";

type Branch = { id: string; nombre: string; es_principal: boolean };
type Report = { key: "ordenes" | "pagos" | "inventario"; title: string; description: string; filename: string; icon: React.ReactNode; period: boolean };
const reports: Report[] = [
  { key: "ordenes", title: "Órdenes de trabajo", description: "Estados, clientes, vehículos, importes, saldos y fechas de atención.", filename: "ordenes_trabajo.csv", icon: <Wrench size={22} />, period: true },
  { key: "pagos", title: "Pagos y anulaciones", description: "Operaciones de caja, métodos, referencias y motivos de anulación.", filename: "pagos.csv", icon: <HandCoins size={22} />, period: true },
  { key: "inventario", title: "Inventario valorizado", description: "Existencias por sucursal, costos, precios y alertas de stock bajo.", filename: "inventario.csv", icon: <Boxes size={22} />, period: false },
];
const isoDate = (date: Date) => date.toISOString().slice(0, 10);
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";

export function ReportesModule() {
  const today = new Date(); const monthAgo = new Date(); monthAgo.setDate(today.getDate() - 29);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchId, setBranchId] = useState("");
  const [from, setFrom] = useState(isoDate(monthAgo));
  const [to, setTo] = useState(isoDate(today));
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { const timer = window.setTimeout(async () => { try { setBranches(await apiRequest<Branch[]>("/sucursales")); } catch (requestError) { setError(errorText(requestError)); } }, 0); return () => window.clearTimeout(timer); }, []);

  async function download(report: Report) {
    setDownloading(report.key); setError("");
    const query = new URLSearchParams();
    if (branchId) query.set("sucursal_id", branchId);
    if (report.period) { query.set("desde", from); query.set("hasta", to); }
    try {
      const response = await fetch(`/api/backend/reportes/${report.key}?${query}`);
      if (!response.ok) { const body = await response.json().catch(() => null); throw new ApiError(body?.detail || "No se pudo generar el reporte", response.status); }
      const blob = await response.blob(); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = report.filename; anchor.click(); URL.revokeObjectURL(url);
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setDownloading(null); }
  }

  return <div className="space-y-5">
    <PageHeading title="Reportes y exportaciones" subtitle="Descarga información operativa compatible con Excel y otros sistemas." />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    <section className="grid gap-3 rounded-2xl border bg-white p-4 shadow-sm sm:grid-cols-3"><Field label="Desde"><input type="date" className="form-control" value={from} max={to} onChange={(event) => setFrom(event.target.value)} /></Field><Field label="Hasta"><input type="date" className="form-control" value={to} min={from} onChange={(event) => setTo(event.target.value)} /></Field><Field label="Sucursal"><select className="form-control" value={branchId} onChange={(event) => setBranchId(event.target.value)}><option value="">Todas las sucursales</option>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.nombre}{branch.es_principal ? " · Principal" : ""}</option>)}</select></Field></section>
    <div className="grid gap-4 lg:grid-cols-3">{reports.map((report) => <article key={report.key} className="flex min-h-64 flex-col rounded-2xl border bg-white p-5 shadow-sm"><span className="grid size-12 place-items-center rounded-xl bg-blue-50 text-blue-600">{report.icon}</span><h2 className="mt-5 text-lg font-bold">{report.title}</h2><p className="mt-2 flex-1 text-sm leading-6 text-slate-500">{report.description}</p><div className="mt-5 rounded-xl bg-slate-50 p-3 text-xs text-slate-500"><FileDown size={14} className="mr-1 inline" />Archivo CSV separado por punto y coma, compatible con Excel.</div><button className="button primary mt-4 w-full" disabled={Boolean(downloading)} onClick={() => void download(report)}>{downloading === report.key ? <LoaderCircle size={16} className="animate-spin" /> : <Download size={16} />}{downloading === report.key ? "Generando…" : "Descargar reporte"}</button></article>)}</div>
    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800"><strong>Privacidad multiempresa:</strong> cada archivo contiene únicamente información de la empresa activa en tu sesión.</div>
  </div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
