"use client";

import { Building2, Palette, ReceiptText, Save, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";

type Config = {
  nombre_comercial: string; razon_social: string; ruc: string; logo_url: string | null;
  direccion_fiscal: string | null; telefono: string | null; email: string | null;
  sitio_web: string | null; color_primario: string; moneda: string;
  porcentaje_impuesto: string; zona_horaria: string;
  prefijo_orden: string; prefijo_cotizacion: string;
};
const empty: Config = { nombre_comercial: "", razon_social: "", ruc: "", logo_url: null, direccion_fiscal: null, telefono: null, email: null, sitio_web: null, color_primario: "#2563EB", moneda: "PEN", porcentaje_impuesto: "18", zona_horaria: "America/Lima", prefijo_orden: "OT", prefijo_cotizacion: "COT" };
const message = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";

export function ConfiguracionModule() {
  const [form, setForm] = useState<Config>(empty);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try { setForm(await apiRequest<Config>("/configuracion")); }
      catch (requestError) { setError(message(requestError)); }
      finally { setLoading(false); }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  function patch(key: keyof Config, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
    setSaved(false);
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      setForm(await apiRequest<Config>("/configuracion", { method: "PUT", body: JSON.stringify({ ...form, porcentaje_impuesto: Number(form.porcentaje_impuesto), logo_url: form.logo_url || null, direccion_fiscal: form.direccion_fiscal || null, telefono: form.telefono || null, email: form.email || null, sitio_web: form.sitio_web || null }) }));
      setSaved(true);
    } catch (requestError) { setError(message(requestError)); }
    finally { setSaving(false); }
  }

  if (loading) return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">Cargando configuración…</div>;
  return <form className="space-y-5" onSubmit={save}>
    <PageHeading title="Configuración de empresa" subtitle="Personaliza los datos y valores usados en documentos y operaciones." action={<button disabled={saving} className="button primary"><Save size={16} />{saving ? "Guardando…" : "Guardar cambios"}</button>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button type="button" onClick={() => setError("")}><X size={16} /></button></div> : null}
    {saved ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">Configuración guardada correctamente. Vuelve a iniciar sesión para actualizar el nombre y color del menú.</div> : null}
    <Section icon={<Building2 size={18} />} title="Identidad y datos fiscales">
      <div className="grid gap-3 sm:grid-cols-2"><Field label="Nombre comercial"><input required className="form-control" value={form.nombre_comercial} onChange={(event) => patch("nombre_comercial", event.target.value)} /></Field><Field label="Razón social"><input required className="form-control" value={form.razon_social} onChange={(event) => patch("razon_social", event.target.value)} /></Field><Field label="RUC"><input required inputMode="numeric" minLength={11} maxLength={11} className="form-control" value={form.ruc} onChange={(event) => patch("ruc", event.target.value.replace(/\D/g, ""))} /></Field><Field label="Dirección fiscal"><input className="form-control" value={form.direccion_fiscal || ""} onChange={(event) => patch("direccion_fiscal", event.target.value)} /></Field><Field label="Teléfono"><input className="form-control" value={form.telefono || ""} onChange={(event) => patch("telefono", event.target.value)} /></Field><Field label="Correo"><input type="email" className="form-control" value={form.email || ""} onChange={(event) => patch("email", event.target.value)} /></Field><Field label="Sitio web"><input className="form-control" placeholder="https://…" value={form.sitio_web || ""} onChange={(event) => patch("sitio_web", event.target.value)} /></Field><Field label="URL del logo"><input className="form-control" placeholder="https://…" value={form.logo_url || ""} onChange={(event) => patch("logo_url", event.target.value)} /></Field></div>
    </Section>
    <div className="grid gap-5 xl:grid-cols-2"><Section icon={<ReceiptText size={18} />} title="Operación y documentos"><div className="grid gap-3 sm:grid-cols-2"><Field label="Moneda"><select className="form-control" value={form.moneda} onChange={(event) => patch("moneda", event.target.value)}><option value="PEN">PEN · Sol peruano</option><option value="USD">USD · Dólar</option></select></Field><Field label="Impuesto (%)"><input required type="number" min="0" max="100" step="0.01" className="form-control" value={form.porcentaje_impuesto} onChange={(event) => patch("porcentaje_impuesto", event.target.value)} /></Field><Field label="Prefijo de órdenes"><input required maxLength={10} className="form-control uppercase" value={form.prefijo_orden} onChange={(event) => patch("prefijo_orden", event.target.value)} /></Field><Field label="Prefijo de cotizaciones"><input required maxLength={10} className="form-control uppercase" value={form.prefijo_cotizacion} onChange={(event) => patch("prefijo_cotizacion", event.target.value)} /></Field><Field label="Zona horaria"><select className="form-control" value={form.zona_horaria} onChange={(event) => patch("zona_horaria", event.target.value)}><option value="America/Lima">America/Lima</option><option value="America/Bogota">America/Bogota</option><option value="America/Mexico_City">America/Mexico City</option><option value="America/Santiago">America/Santiago</option></select></Field></div></Section>
      <Section icon={<Palette size={18} />} title="Apariencia"><div className="flex items-center gap-4"><input type="color" className="h-14 w-20 rounded-xl border bg-white p-1" value={form.color_primario} onChange={(event) => patch("color_primario", event.target.value.toUpperCase())} /><div><div className="font-semibold">Color principal</div><div className="text-sm text-slate-500">{form.color_primario}</div></div></div><div className="mt-5 rounded-2xl p-5 text-white" style={{ backgroundColor: form.color_primario }}><div className="text-xs opacity-80">Vista previa</div><div className="mt-1 text-xl font-black">{form.nombre_comercial || "Nombre del taller"}</div><div className="mt-4 inline-flex rounded-lg bg-white/20 px-3 py-2 text-sm font-semibold">Acción principal</div></div></Section></div>
  </form>;
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) { return <section className="rounded-2xl border bg-white p-5 shadow-sm"><div className="mb-5 flex items-center gap-2 border-b pb-4 text-blue-700">{icon}<h2 className="font-bold text-slate-900">{title}</h2></div>{children}</section>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
