"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Building2, Plus, Users, X } from "lucide-react";
import { ApiError, apiRequest } from "@/lib/api";
import { PageHeading } from "@/components/ui/page-heading";

type Summary = { empresas_total: number; empresas_activas: number; empresas_prueba: number; empresas_vencidas: number; usuarios_activos: number };
type Company = {
  id: string; nombre_comercial: string; razon_social: string; ruc: string; email: string | null;
  telefono: string | null; estado: string; plan_codigo: string; suscripcion_estado: string;
  suscripcion_inicio: string; suscripcion_fin: string | null; max_usuarios: number;
  max_sucursales: number; notas_internas: string | null; usuarios_activos: number;
  sucursales_activas: number; ordenes_total: number; created_at: string;
};

const emptyForm = {
  nombre_comercial: "", razon_social: "", ruc: "", email: "", telefono: "",
  plan_codigo: "basico", suscripcion_fin: "", max_usuarios: 5, max_sucursales: 1,
  admin_email: "", admin_password: "", admin_nombres: "", admin_apellidos: "",
};

export function PlataformaModule() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selected, setSelected] = useState<Company | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [stats, rows] = await Promise.all([
        apiRequest<Summary>("/plataforma/resumen"),
        apiRequest<Company[]>("/plataforma/empresas"),
      ]);
      setSummary(stats); setCompanies(rows); setError("");
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "No se pudo cargar la plataforma");
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function createCompany(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      await apiRequest("/plataforma/empresas", {
        method: "POST",
        body: JSON.stringify({ ...form, email: form.email || null, telefono: form.telefono || null, suscripcion_fin: form.suscripcion_fin || null }),
      });
      setCreating(false); setForm(emptyForm); await load();
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "No se pudo crear la empresa");
    } finally { setSaving(false); }
  }

  async function updateCompany(event: FormEvent) {
    event.preventDefault(); if (!selected) return; setSaving(true); setError("");
    try {
      await apiRequest(`/plataforma/empresas/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          nombre_comercial: selected.nombre_comercial, razon_social: selected.razon_social,
          email: selected.email || null, telefono: selected.telefono || null, estado: selected.estado,
          plan_codigo: selected.plan_codigo, suscripcion_estado: selected.suscripcion_estado,
          suscripcion_fin: selected.suscripcion_fin || null, max_usuarios: selected.max_usuarios,
          max_sucursales: selected.max_sucursales, notas_internas: selected.notas_internas || null,
        }),
      });
      setSelected(null); await load();
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "No se pudo actualizar la empresa");
    } finally { setSaving(false); }
  }

  return <div className="space-y-5">
    <PageHeading title="Administración de la plataforma" subtitle="Empresas, suscripciones y límites del sistema SaaS." action={<button className="button primary" onClick={() => setCreating(true)}><Plus size={16}/> Nueva empresa</button>} />
    {error ? <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Stat label="Empresas" value={summary?.empresas_total} icon={<Building2 size={18}/>} />
      <Stat label="Activas" value={summary?.empresas_activas} />
      <Stat label="En prueba" value={summary?.empresas_prueba} />
      <Stat label="Vencidas" value={summary?.empresas_vencidas} />
      <Stat label="Usuarios" value={summary?.usuarios_activos} icon={<Users size={18}/>} />
    </div>
    <section className="overflow-hidden rounded-2xl border bg-white">
      <div className="overflow-x-auto"><table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="p-4">Empresa</th><th>Plan</th><th>Suscripción</th><th>Uso</th><th>Órdenes</th><th></th></tr></thead>
        <tbody>{companies.map(company => <tr className="border-t" key={company.id}>
          <td className="p-4"><div className="font-bold text-slate-900">{company.nombre_comercial}</div><div className="text-xs text-slate-500">RUC {company.ruc}</div></td>
          <td className="capitalize">{company.plan_codigo}</td>
          <td><span className={`rounded-full px-2 py-1 text-xs font-semibold ${company.suscripcion_estado === "activa" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{company.suscripcion_estado}</span></td>
          <td>{company.usuarios_activos}/{company.max_usuarios} usuarios<br/><span className="text-xs text-slate-500">{company.sucursales_activas}/{company.max_sucursales} sucursales</span></td>
          <td>{company.ordenes_total}</td>
          <td className="pr-4 text-right"><button className="button" onClick={() => setSelected(company)}>Administrar</button></td>
        </tr>)}</tbody>
      </table></div>
      {!companies.length ? <div className="p-10 text-center text-sm text-slate-500">No hay empresas registradas.</div> : null}
    </section>
    {creating ? <Dialog title="Registrar empresa" close={() => setCreating(false)}><form className="grid gap-4 sm:grid-cols-2" onSubmit={createCompany}>
      <Input label="Nombre comercial" value={form.nombre_comercial} set={v=>setForm({...form,nombre_comercial:v})}/>
      <Input label="Razón social" value={form.razon_social} set={v=>setForm({...form,razon_social:v})}/>
      <Input label="RUC" value={form.ruc} set={v=>setForm({...form,ruc:v})} pattern="\d{11}"/>
      <Input label="Correo de la empresa" type="email" value={form.email} set={v=>setForm({...form,email:v})} required={false}/>
      <Select label="Plan" value={form.plan_codigo} set={v=>setForm({...form,plan_codigo:v})} options={["basico","profesional","empresarial"]}/>
      <Input label="Fin de suscripción" type="date" value={form.suscripcion_fin} set={v=>setForm({...form,suscripcion_fin:v})} required={false}/>
      <Input label="Máximo de usuarios" type="number" value={String(form.max_usuarios)} set={v=>setForm({...form,max_usuarios:Number(v)})}/>
      <Input label="Máximo de sucursales" type="number" value={String(form.max_sucursales)} set={v=>setForm({...form,max_sucursales:Number(v)})}/>
      <div className="sm:col-span-2 border-t pt-4 font-bold">Administrador inicial</div>
      <Input label="Nombres" value={form.admin_nombres} set={v=>setForm({...form,admin_nombres:v})}/>
      <Input label="Apellidos" value={form.admin_apellidos} set={v=>setForm({...form,admin_apellidos:v})}/>
      <Input label="Correo de acceso" type="email" value={form.admin_email} set={v=>setForm({...form,admin_email:v})}/>
      <Input label="Contraseña temporal" type="password" value={form.admin_password} set={v=>setForm({...form,admin_password:v})}/>
      <Actions saving={saving} cancel={()=>setCreating(false)}/>
    </form></Dialog> : null}
    {selected ? <Dialog title={`Administrar ${selected.nombre_comercial}`} close={()=>setSelected(null)}><form className="grid gap-4 sm:grid-cols-2" onSubmit={updateCompany}>
      <Input label="Nombre comercial" value={selected.nombre_comercial} set={v=>setSelected({...selected,nombre_comercial:v})}/>
      <Input label="Razón social" value={selected.razon_social} set={v=>setSelected({...selected,razon_social:v})}/>
      <Select label="Plan" value={selected.plan_codigo} set={v=>setSelected({...selected,plan_codigo:v})} options={["basico","profesional","empresarial"]}/>
      <Select label="Suscripción" value={selected.suscripcion_estado} set={v=>setSelected({...selected,suscripcion_estado:v})} options={["prueba","activa","vencida","cancelada"]}/>
      <Select label="Acceso" value={selected.estado} set={v=>setSelected({...selected,estado:v})} options={["activo","suspendido","inactivo"]}/>
      <Input label="Fin de suscripción" type="date" value={selected.suscripcion_fin || ""} set={v=>setSelected({...selected,suscripcion_fin:v || null})} required={false}/>
      <Input label="Máximo de usuarios" type="number" value={String(selected.max_usuarios)} set={v=>setSelected({...selected,max_usuarios:Number(v)})}/>
      <Input label="Máximo de sucursales" type="number" value={String(selected.max_sucursales)} set={v=>setSelected({...selected,max_sucursales:Number(v)})}/>
      <label className="sm:col-span-2 text-xs font-semibold text-slate-600">Notas internas<textarea className="form-control mt-1 min-h-24" value={selected.notas_internas || ""} onChange={e=>setSelected({...selected,notas_internas:e.target.value})}/></label>
      <Actions saving={saving} cancel={()=>setSelected(null)}/>
    </form></Dialog> : null}
  </div>;
}

function Stat({label,value,icon}:{label:string;value?:number;icon?:React.ReactNode}) { return <div className="rounded-2xl border bg-white p-4"><div className="flex items-center justify-between text-xs font-semibold text-slate-500">{label}{icon}</div><div className="mt-2 text-2xl font-black">{value ?? "—"}</div></div> }
function Dialog({title,close,children}:{title:string;close:()=>void;children:React.ReactNode}) { return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4"><div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="flex items-center justify-between border-b p-5"><h2 className="font-bold">{title}</h2><button onClick={close} type="button"><X size={20}/></button></div><div className="p-5">{children}</div></div></div> }
function Input({label,value,set,type="text",required=true,pattern}:{label:string;value:string;set:(v:string)=>void;type?:string;required?:boolean;pattern?:string}) { return <label className="text-xs font-semibold text-slate-600">{label}<input className="form-control mt-1" type={type} required={required} pattern={pattern} min={type==="number"?"1":undefined} value={value} onChange={e=>set(e.target.value)}/></label> }
function Select({label,value,set,options}:{label:string;value:string;set:(v:string)=>void;options:string[]}) { return <label className="text-xs font-semibold text-slate-600">{label}<select className="form-control mt-1 capitalize" value={value} onChange={e=>set(e.target.value)}>{options.map(x=><option key={x}>{x}</option>)}</select></label> }
function Actions({saving,cancel}:{saving:boolean;cancel:()=>void}) { return <div className="flex justify-end gap-2 sm:col-span-2"><button type="button" className="button" onClick={cancel}>Cancelar</button><button className="button primary" disabled={saving}>{saving?"Guardando…":"Guardar"}</button></div> }
