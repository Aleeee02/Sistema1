"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Bell, Building2, CreditCard, History, Plus, RefreshCw, Settings2, Users, X } from "lucide-react";
import { ApiError, apiRequest } from "@/lib/api";
import { PageHeading } from "@/components/ui/page-heading";

type Summary = { empresas_total: number; empresas_activas: number; empresas_prueba: number; empresas_vencidas: number; usuarios_activos: number };
type Company = {
  id: string; nombre_comercial: string; razon_social: string; ruc: string; email: string | null;
  telefono: string | null; estado: string; plan_codigo: string; suscripcion_estado: string;
  suscripcion_inicio: string; suscripcion_fin: string | null; max_usuarios: number;
  max_sucursales: number; notas_internas: string | null; usuarios_activos: number;
  dias_gracia: number; sucursales_activas: number; ordenes_total: number; created_at: string;
};
type Plan = {
  id: string; codigo: string; nombre: string; descripcion: string | null;
  precio_mensual: string; max_usuarios: number; max_sucursales: number;
  modulos: string[]; estado: string;
};
type Payment = { id:string; monto:string; ciclo:string; metodo_pago:string; referencia:string|null; periodo_inicio:string; periodo_fin:string; pagado_at:string };
type Alert = { id:string; empresa_nombre:string; tipo:string; fecha_vencimiento:string; destinatario:string; estado:string; error:string|null; created_at:string };

const moduleOptions = [
  ["agenda","Agenda"],["clientes","Clientes"],["vehiculos","Vehículos"],
  ["ordenes","Órdenes"],["cotizaciones","Cotizaciones"],["inspecciones","Inspecciones"],
  ["pagos","Pagos"],["servicios","Servicios"],["inventario","Inventario"],
  ["transferencias","Transferencias"],["empleados","Empleados"],["sucursales","Sucursales"],
  ["usuarios","Usuarios y roles"],["estadisticas","Estadísticas"],["reportes","Reportes"],
  ["configuracion","Configuración"],["comprobantes","Comprobantes"],["auditoria","Auditoría"],
] as const;

const emptyForm = {
  nombre_comercial: "", razon_social: "", ruc: "", email: "", telefono: "",
  plan_codigo: "basico", suscripcion_fin: "", max_usuarios: 5, max_sucursales: 1,
  admin_email: "", admin_password: "", admin_nombres: "", admin_apellidos: "",
};

export function PlataformaModule() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [editingPlan, setEditingPlan] = useState<Plan | null>(null);
  const [payingCompany, setPayingCompany] = useState<Company | null>(null);
  const [historyCompany, setHistoryCompany] = useState<Company | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [payment, setPayment] = useState({monto:"",ciclo:"mensual",metodo_pago:"transferencia",referencia:"",observaciones:""});
  const [selected, setSelected] = useState<Company | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [stats, rows, planRows, alertRows] = await Promise.all([
        apiRequest<Summary>("/plataforma/resumen"),
        apiRequest<Company[]>("/plataforma/empresas"),
        apiRequest<Plan[]>("/plataforma/planes"),
        apiRequest<Alert[]>("/plataforma/alertas"),
      ]);
      setSummary(stats); setCompanies(rows); setPlans(planRows); setAlerts(alertRows); setError("");
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
          max_sucursales: selected.max_sucursales, dias_gracia: selected.dias_gracia,
          notas_internas: selected.notas_internas || null,
        }),
      });
      setSelected(null); await load();
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "No se pudo actualizar la empresa");
    } finally { setSaving(false); }
  }

  async function updatePlan(event: FormEvent) {
    event.preventDefault(); if (!editingPlan) return; setSaving(true); setError("");
    try {
      await apiRequest(`/plataforma/planes/${editingPlan.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          nombre: editingPlan.nombre, descripcion: editingPlan.descripcion,
          precio_mensual: editingPlan.precio_mensual,
          max_usuarios: editingPlan.max_usuarios, max_sucursales: editingPlan.max_sucursales,
          modulos: editingPlan.modulos, estado: editingPlan.estado,
        }),
      });
      setEditingPlan(null); await load();
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "No se pudo actualizar el plan");
    } finally { setSaving(false); }
  }

  async function registerPayment(event: FormEvent) {
    event.preventDefault(); if (!payingCompany) return; setSaving(true); setError("");
    try {
      await apiRequest(`/plataforma/empresas/${payingCompany.id}/pagos`, {
        method:"POST", body:JSON.stringify({...payment,monto:Number(payment.monto),referencia:payment.referencia||null,observaciones:payment.observaciones||null}),
      });
      setPayingCompany(null); setPayment({monto:"",ciclo:"mensual",metodo_pago:"transferencia",referencia:"",observaciones:""}); await load();
    } catch(value) { setError(value instanceof ApiError?value.message:"No se pudo registrar el pago"); }
    finally { setSaving(false); }
  }

  async function openHistory(company:Company) {
    setHistoryCompany(company);
    try { setPayments(await apiRequest<Payment[]>(`/plataforma/empresas/${company.id}/pagos`)); }
    catch(value) { setError(value instanceof ApiError?value.message:"No se pudo cargar el historial"); }
  }

  async function processAlerts() {
    setSaving(true); setError("");
    try { await apiRequest("/plataforma/alertas/procesar",{method:"POST"}); await load(); }
    catch(value) { setError(value instanceof ApiError?value.message:"No se pudieron procesar las alertas"); }
    finally { setSaving(false); }
  }

  return <div className="space-y-5">
    <PageHeading title="Administración de la plataforma" subtitle="Empresas, suscripciones y límites del sistema SaaS." action={<div className="flex gap-2"><button className="button" disabled={!plans.length} onClick={() => setEditingPlan(plans[0])}><Settings2 size={16}/> Configurar planes</button><button className="button primary" onClick={() => setCreating(true)}><Plus size={16}/> Nueva empresa</button></div>} />
    {error ? <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Stat label="Empresas" value={summary?.empresas_total} icon={<Building2 size={18}/>} />
      <Stat label="Activas" value={summary?.empresas_activas} />
      <Stat label="En prueba" value={summary?.empresas_prueba} />
      <Stat label="Vencidas" value={summary?.empresas_vencidas} />
      <Stat label="Usuarios" value={summary?.usuarios_activos} icon={<Users size={18}/>} />
    </div>
    <section className="rounded-2xl border bg-white p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="flex items-center gap-2 font-bold"><Bell size={18} className="text-amber-500"/> Alertas de suscripción</h2><p className="text-xs text-slate-500">Correos enviados por vencimientos y periodos de gracia.</p></div><button className="button" disabled={saving} onClick={()=>void processAlerts()}><RefreshCw size={15}/> Revisar ahora</button></div>
      <div className="grid gap-3 lg:grid-cols-3">{alerts.slice(0,6).map(alert=><div className="rounded-xl border p-3" key={alert.id}><div className="flex items-start justify-between gap-2"><div className="font-semibold">{alert.empresa_nombre}</div><span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${alert.estado==="enviada"?"bg-emerald-50 text-emerald-700":"bg-red-50 text-red-700"}`}>{alert.estado}</span></div><div className="mt-1 text-xs capitalize text-slate-500">{alert.tipo.replaceAll("_"," ")} · vence {alert.fecha_vencimiento}</div><div className="mt-1 truncate text-xs text-slate-400">{alert.destinatario}</div></div>)}</div>
      {!alerts.length?<div className="rounded-xl bg-slate-50 p-4 text-center text-sm text-slate-500">No hay alertas generadas.</div>:null}
    </section>
    <section className="overflow-hidden rounded-2xl border bg-white">
      <div className="overflow-x-auto"><table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="p-4">Empresa</th><th>Plan</th><th>Suscripción</th><th>Uso</th><th>Órdenes</th><th></th></tr></thead>
        <tbody>{companies.map(company => <tr className="border-t" key={company.id}>
          <td className="p-4"><div className="font-bold text-slate-900">{company.nombre_comercial}</div><div className="text-xs text-slate-500">RUC {company.ruc}</div></td>
          <td className="capitalize">{company.plan_codigo}</td>
          <td><span className={`rounded-full px-2 py-1 text-xs font-semibold ${company.suscripcion_estado === "activa" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{company.suscripcion_estado}</span></td>
          <td>{company.usuarios_activos}/{company.max_usuarios} usuarios<br/><span className="text-xs text-slate-500">{company.sucursales_activas}/{company.max_sucursales} sucursales</span></td>
          <td>{company.ordenes_total}</td>
          <td className="pr-4"><div className="flex justify-end gap-2"><button className="button" title="Historial" onClick={() => void openHistory(company)}><History size={15}/></button><button className="button" onClick={() => {setPayingCompany(company);setPayment({...payment,monto:plans.find(p=>p.codigo===company.plan_codigo)?.precio_mensual||""})}}><CreditCard size={15}/> Cobrar</button><button className="button" onClick={() => setSelected(company)}>Administrar</button></div></td>
        </tr>)}</tbody>
      </table></div>
      {!companies.length ? <div className="p-10 text-center text-sm text-slate-500">No hay empresas registradas.</div> : null}
    </section>
    {creating ? <Dialog title="Registrar empresa" close={() => setCreating(false)}><form className="grid gap-4 sm:grid-cols-2" onSubmit={createCompany}>
      <Input label="Nombre comercial" value={form.nombre_comercial} set={v=>setForm({...form,nombre_comercial:v})}/>
      <Input label="Razón social" value={form.razon_social} set={v=>setForm({...form,razon_social:v})}/>
      <Input label="RUC" value={form.ruc} set={v=>setForm({...form,ruc:v})} pattern="\d{11}"/>
      <Input label="Correo de la empresa" type="email" value={form.email} set={v=>setForm({...form,email:v})} required={false}/>
      <Select label="Plan" value={form.plan_codigo} set={v=>setForm({...form,plan_codigo:v})} options={plans.filter(p=>p.estado==="activo").map(p=>p.codigo)}/>
      <Input label="Fin de suscripción" type="date" value={form.suscripcion_fin} set={v=>setForm({...form,suscripcion_fin:v})} required={false}/>
      <div className="sm:col-span-2 rounded-xl bg-blue-50 p-3 text-sm text-blue-800">El plan seleccionado asignará automáticamente sus límites y módulos.</div>
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
      <Select label="Plan" value={selected.plan_codigo} set={v=>{const p=plans.find(x=>x.codigo===v);setSelected({...selected,plan_codigo:v,max_usuarios:p?.max_usuarios??selected.max_usuarios,max_sucursales:p?.max_sucursales??selected.max_sucursales})}} options={plans.filter(p=>p.estado==="activo").map(p=>p.codigo)}/>
      <Select label="Suscripción" value={selected.suscripcion_estado} set={v=>setSelected({...selected,suscripcion_estado:v})} options={["prueba","activa","vencida","cancelada"]}/>
      <Select label="Acceso" value={selected.estado} set={v=>setSelected({...selected,estado:v})} options={["activo","suspendido","inactivo"]}/>
      <Input label="Fin de suscripción" type="date" value={selected.suscripcion_fin || ""} set={v=>setSelected({...selected,suscripcion_fin:v || null})} required={false}/>
      <Input label="Máximo de usuarios" type="number" value={String(selected.max_usuarios)} set={v=>setSelected({...selected,max_usuarios:Number(v)})}/>
      <Input label="Máximo de sucursales" type="number" value={String(selected.max_sucursales)} set={v=>setSelected({...selected,max_sucursales:Number(v)})}/>
      <Input label="Días de gracia" type="number" value={String(selected.dias_gracia)} set={v=>setSelected({...selected,dias_gracia:Number(v)})}/>
      <label className="sm:col-span-2 text-xs font-semibold text-slate-600">Notas internas<textarea className="form-control mt-1 min-h-24" value={selected.notas_internas || ""} onChange={e=>setSelected({...selected,notas_internas:e.target.value})}/></label>
      <Actions saving={saving} cancel={()=>setSelected(null)}/>
    </form></Dialog> : null}
    {payingCompany ? <Dialog title={`Registrar cobro · ${payingCompany.nombre_comercial}`} close={()=>setPayingCompany(null)}><form className="grid gap-4 sm:grid-cols-2" onSubmit={registerPayment}>
      <Input label="Monto (S/)" type="number" value={payment.monto} set={v=>setPayment({...payment,monto:v})}/>
      <Select label="Ciclo de renovación" value={payment.ciclo} set={v=>setPayment({...payment,ciclo:v})} options={["mensual","trimestral","semestral","anual"]}/>
      <Select label="Método de pago" value={payment.metodo_pago} set={v=>setPayment({...payment,metodo_pago:v})} options={["yape","plin","transferencia","efectivo","tarjeta","otro"]}/>
      <Input label="Número de operación o referencia" value={payment.referencia} set={v=>setPayment({...payment,referencia:v})} required={false}/>
      <label className="sm:col-span-2 text-xs font-semibold text-slate-600">Observaciones<textarea className="form-control mt-1" value={payment.observaciones} onChange={e=>setPayment({...payment,observaciones:e.target.value})}/></label>
      <div className="sm:col-span-2 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">Al confirmar, la suscripción quedará activa y su vencimiento se extenderá según el ciclo.</div>
      <Actions saving={saving} cancel={()=>setPayingCompany(null)}/>
    </form></Dialog> : null}
    {historyCompany ? <Dialog title={`Historial · ${historyCompany.nombre_comercial}`} close={()=>setHistoryCompany(null)}><div className="space-y-3">{payments.map(item=><div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4" key={item.id}><div><div className="font-bold">S/ {Number(item.monto).toFixed(2)} · <span className="capitalize">{item.ciclo}</span></div><div className="text-xs text-slate-500">{item.periodo_inicio} al {item.periodo_fin}</div></div><div className="text-right text-sm capitalize">{item.metodo_pago}<div className="text-xs text-slate-500">{item.referencia||"Sin referencia"}</div></div></div>)}{!payments.length?<div className="py-10 text-center text-sm text-slate-500">Aún no hay pagos registrados.</div>:null}</div></Dialog> : null}
    {editingPlan ? <Dialog title="Configurar planes" close={()=>setEditingPlan(null)}><div className="mb-5 flex flex-wrap gap-2">{plans.map(plan=><button type="button" className={`button ${editingPlan.id===plan.id?"primary":""}`} key={plan.id} onClick={()=>setEditingPlan(plan)}>{plan.nombre}</button>)}</div><form className="grid gap-4 sm:grid-cols-2" onSubmit={updatePlan}>
      <Input label="Nombre" value={editingPlan.nombre} set={v=>setEditingPlan({...editingPlan,nombre:v})}/>
      <Input label="Precio mensual (S/)" type="number" value={editingPlan.precio_mensual} set={v=>setEditingPlan({...editingPlan,precio_mensual:v})}/>
      <Input label="Usuarios incluidos" type="number" value={String(editingPlan.max_usuarios)} set={v=>setEditingPlan({...editingPlan,max_usuarios:Number(v)})}/>
      <Input label="Sucursales incluidas" type="number" value={String(editingPlan.max_sucursales)} set={v=>setEditingPlan({...editingPlan,max_sucursales:Number(v)})}/>
      <label className="sm:col-span-2 text-xs font-semibold text-slate-600">Descripción<textarea className="form-control mt-1" value={editingPlan.descripcion || ""} onChange={e=>setEditingPlan({...editingPlan,descripcion:e.target.value})}/></label>
      <div className="sm:col-span-2"><div className="mb-2 text-xs font-semibold text-slate-600">Módulos incluidos</div><div className="grid gap-2 sm:grid-cols-3">{moduleOptions.map(([code,label])=><label className="flex items-center gap-2 rounded-xl border p-3 text-sm" key={code}><input type="checkbox" checked={editingPlan.modulos.includes(code)} onChange={e=>setEditingPlan({...editingPlan,modulos:e.target.checked?[...editingPlan.modulos,code]:editingPlan.modulos.filter(x=>x!==code)})}/>{label}</label>)}</div></div>
      <Actions saving={saving} cancel={()=>setEditingPlan(null)}/>
    </form></Dialog> : null}
  </div>;
}

function Stat({label,value,icon}:{label:string;value?:number;icon?:React.ReactNode}) { return <div className="rounded-2xl border bg-white p-4"><div className="flex items-center justify-between text-xs font-semibold text-slate-500">{label}{icon}</div><div className="mt-2 text-2xl font-black">{value ?? "—"}</div></div> }
function Dialog({title,close,children}:{title:string;close:()=>void;children:React.ReactNode}) { return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4"><div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="flex items-center justify-between border-b p-5"><h2 className="font-bold">{title}</h2><button onClick={close} type="button"><X size={20}/></button></div><div className="p-5">{children}</div></div></div> }
function Input({label,value,set,type="text",required=true,pattern}:{label:string;value:string;set:(v:string)=>void;type?:string;required?:boolean;pattern?:string}) { return <label className="text-xs font-semibold text-slate-600">{label}<input className="form-control mt-1" type={type} required={required} pattern={pattern} min={type==="number"?"0":undefined} step={type==="number"?"0.01":undefined} value={value} onChange={e=>set(e.target.value)}/></label> }
function Select({label,value,set,options}:{label:string;value:string;set:(v:string)=>void;options:string[]}) { return <label className="text-xs font-semibold text-slate-600">{label}<select className="form-control mt-1 capitalize" value={value} onChange={e=>set(e.target.value)}>{options.map(x=><option key={x}>{x}</option>)}</select></label> }
function Actions({saving,cancel}:{saving:boolean;cancel:()=>void}) { return <div className="flex justify-end gap-2 sm:col-span-2"><button type="button" className="button" onClick={cancel}>Cancelar</button><button className="button primary" disabled={saving}>{saving?"Guardando…":"Guardar"}</button></div> }
