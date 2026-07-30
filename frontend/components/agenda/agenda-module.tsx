"use client";

import { CalendarDays, ChevronLeft, ChevronRight, Clock3, MapPin, Plus, Settings2, UserRound, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiError, apiRequest } from "@/lib/api";
import { usePermissions } from "@/lib/use-permissions";

type Branch = { id: string; nombre: string; es_principal: boolean };
type Bay = { id: string; sucursal_id: string; sucursal_nombre: string; nombre: string; codigo: string; descripcion: string | null; estado: string };
type Client = { id: string; nombre: string };
type Vehicle = { id: string; cliente_id: string; placa: string; descripcion: string };
type Employee = { id: string; sucursal_id: string; nombre: string };
type Appointment = { id: string; sucursal_id: string; sucursal_nombre: string; cliente_id: string; cliente_nombre: string; vehiculo_id: string; vehiculo_placa: string; vehiculo_descripcion: string; bahia_id: string | null; bahia_nombre: string | null; empleado_id: string | null; empleado_nombre: string | null; fecha_inicio: string; fecha_fin: string; motivo: string; estado: string; observaciones: string | null };
type Form = { cliente_id: string; vehiculo_id: string; bahia_id: string; empleado_id: string; inicio: string; fin: string; motivo: string; observaciones: string };
const labels: Record<string, string> = { programada: "Programada", confirmada: "Confirmada", atendida: "Atendida", cancelada: "Cancelada", no_asistio: "No asistió" };
const emptyForm: Form = { cliente_id: "", vehiculo_id: "", bahia_id: "", empleado_id: "", inicio: "09:00", fin: "10:00", motivo: "", observaciones: "" };
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";
const isoDate = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

export function AgendaModule() {
  const { can } = usePermissions();
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchId, setBranchId] = useState("");
  const [bays, setBays] = useState<Bay[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [date, setDate] = useState(isoDate(new Date()));
  const [selected, setSelected] = useState<Appointment | null>(null);
  const [form, setForm] = useState<Form>(emptyForm);
  const [appointmentModal, setAppointmentModal] = useState(false);
  const [bayModal, setBayModal] = useState(false);
  const [bayForm, setBayForm] = useState({ codigo: "", nombre: "", descripcion: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadDay = useCallback(async (currentBranch: string, currentDate: string) => {
    if (!currentBranch) return;
    setLoading(true);
    try {
      const start = new Date(`${currentDate}T00:00:00`);
      const end = new Date(start); end.setDate(end.getDate() + 1);
      const [day, bayData] = await Promise.all([
        apiRequest<Appointment[]>(`/agenda/citas?${new URLSearchParams({ sucursal_id: currentBranch, desde: start.toISOString(), hasta: end.toISOString() })}`),
        apiRequest<Bay[]>(`/agenda/bahias?sucursal_id=${currentBranch}`),
      ]);
      setAppointments(day); setBays(bayData);
      setSelected((value) => value ? day.find((item) => item.id === value.id) || null : null);
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        const [branchData, options] = await Promise.all([apiRequest<Branch[]>("/sucursales"), apiRequest<{ clientes: Client[]; vehiculos: Vehicle[]; empleados: Employee[] }>("/agenda/opciones")]);
        setBranches(branchData); setClients(options.clientes); setVehicles(options.vehiculos); setEmployees(options.empleados);
        const initial = branchData[0]?.id || ""; setBranchId(initial); if (initial) await loadDay(initial, date);
      } catch (requestError) { setError(errorText(requestError)); setLoading(false); }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [date, loadDay]);
  useEffect(() => { if (!branchId) return; const timer = window.setTimeout(() => void loadDay(branchId, date), 0); return () => window.clearTimeout(timer); }, [branchId, date, loadDay]);

  const activeBays = bays.filter((bay) => bay.estado === "activo");
  const availableEmployees = employees.filter((employee) => employee.sucursal_id === branchId);
  const availableVehicles = vehicles.filter((vehicle) => vehicle.cliente_id === form.cliente_id);
  const metrics = useMemo(() => ({ confirmed: appointments.filter((item) => item.estado === "confirmada").length, attended: appointments.filter((item) => item.estado === "atendida").length }), [appointments]);
  function moveDay(amount: number) { const value = new Date(`${date}T12:00:00`); value.setDate(value.getDate() + amount); setDate(isoDate(value)); }
  function openAppointment() { setForm(emptyForm); setAppointmentModal(true); }
  async function createAppointment(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      await apiRequest<Appointment>("/agenda/citas", { method: "POST", body: JSON.stringify({ sucursal_id: branchId, cliente_id: form.cliente_id, vehiculo_id: form.vehiculo_id, bahia_id: form.bahia_id || null, empleado_id: form.empleado_id || null, fecha_inicio: new Date(`${date}T${form.inicio}:00`).toISOString(), fecha_fin: new Date(`${date}T${form.fin}:00`).toISOString(), motivo: form.motivo, observaciones: form.observaciones || null }) });
      setAppointmentModal(false); await loadDay(branchId, date);
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setSaving(false); }
  }
  async function createBay(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      await apiRequest<Bay>("/agenda/bahias", { method: "POST", body: JSON.stringify({ sucursal_id: branchId, ...bayForm, descripcion: bayForm.descripcion || null }) });
      setBayModal(false); setBayForm({ codigo: "", nombre: "", descripcion: "" }); await loadDay(branchId, date);
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setSaving(false); }
  }
  async function changeStatus(estado: string) {
    if (!selected) return;
    try { const updated = await apiRequest<Appointment>(`/agenda/citas/${selected.id}/estado`, { method: "PATCH", body: JSON.stringify({ estado }) }); setSelected(updated); await loadDay(branchId, date); }
    catch (requestError) { setError(errorText(requestError)); }
  }

  return <div className="space-y-5">
    <PageHeading title="Agenda y bahías" subtitle="Programa citas sin duplicar mecánicos ni espacios de trabajo." action={<div className="flex gap-2">{can("agenda.configurar") ? <button className="button" disabled={!branchId} onClick={() => setBayModal(true)}><Settings2 size={16} /> Bahías</button> : null}{can("agenda.citas") ? <button className="button primary" disabled={!branchId} onClick={openAppointment}><Plus size={16} /> Nueva cita</button> : null}</div>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    <div className="grid gap-3 sm:grid-cols-3"><Metric label="Citas del día" value={appointments.length} /><Metric label="Confirmadas" value={metrics.confirmed} /><Metric label="Atendidas" value={metrics.attended} /></div>
    <div className="flex flex-col gap-3 rounded-xl border bg-white p-3 shadow-sm sm:flex-row sm:items-center"><select className="form-control sm:max-w-64" value={branchId} onChange={(event) => setBranchId(event.target.value)}>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.nombre}{branch.es_principal ? " · Principal" : ""}</option>)}</select><div className="flex flex-1 items-center justify-center gap-2"><button className="button" onClick={() => moveDay(-1)}><ChevronLeft size={16} /></button><input type="date" className="form-control max-w-44 text-center font-semibold" value={date} onChange={(event) => setDate(event.target.value)} /><button className="button" onClick={() => moveDay(1)}><ChevronRight size={16} /></button></div><button className="button" onClick={() => setDate(isoDate(new Date()))}>Hoy</button></div>
    <div className="grid gap-4 xl:grid-cols-[1fr_0.8fr]">
      <section className="space-y-3">{loading ? <Empty text="Cargando agenda…" /> : appointments.length === 0 ? <Empty text="No hay citas programadas para este día." /> : appointments.map((item) => <button key={item.id} onClick={() => setSelected(item)} className={`grid w-full gap-3 rounded-xl border bg-white p-4 text-left shadow-sm sm:grid-cols-[90px_1fr_auto] ${selected?.id === item.id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"}`}><div><div className="text-lg font-black text-blue-700">{new Date(item.fecha_inicio).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })}</div><div className="text-xs text-slate-400">{new Date(item.fecha_fin).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })}</div></div><div><h3 className="font-semibold">{item.cliente_nombre} · {item.vehiculo_placa}</h3><p className="mt-1 text-sm text-slate-600">{item.motivo}</p><div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500"><span className="flex items-center gap-1"><MapPin size={13} />{item.bahia_nombre || "Sin bahía"}</span><span className="flex items-center gap-1"><UserRound size={13} />{item.empleado_nombre || "Sin mecánico"}</span></div></div><StatusBadge status={item.estado} label={labels[item.estado]} /></button>)}</section>
      <section className="rounded-2xl border bg-white p-5 shadow-sm">{!selected ? <div className="flex min-h-80 flex-col items-center justify-center text-sm text-slate-500"><CalendarDays className="mb-3 text-blue-600" /><span>Selecciona una cita</span></div> : <><div className="flex items-start justify-between border-b pb-4"><div><h2 className="text-xl font-bold">{selected.vehiculo_placa}</h2><p className="text-sm text-slate-500">{selected.cliente_nombre}</p></div><StatusBadge status={selected.estado} label={labels[selected.estado]} /></div><div className="space-y-3 py-5"><Info icon={<Clock3 size={16} />} label="Horario" value={`${new Date(selected.fecha_inicio).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })} – ${new Date(selected.fecha_fin).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })}`} /><Info icon={<MapPin size={16} />} label="Bahía" value={selected.bahia_nombre || "No asignada"} /><Info icon={<UserRound size={16} />} label="Mecánico" value={selected.empleado_nombre || "No asignado"} /></div><div className="rounded-xl bg-slate-50 p-4"><strong className="text-sm">{selected.motivo}</strong>{selected.observaciones ? <p className="mt-2 text-sm text-slate-600">{selected.observaciones}</p> : null}</div>{can("agenda.citas") ? <div className="mt-5 flex flex-wrap justify-end gap-2 border-t pt-4">{selected.estado === "programada" ? <button className="button primary" onClick={() => void changeStatus("confirmada")}>Confirmar</button> : null}{["programada", "confirmada"].includes(selected.estado) ? <><button className="button" onClick={() => void changeStatus("no_asistio")}>No asistió</button><button className="button text-red-600" onClick={() => void changeStatus("cancelada")}>Cancelar</button></> : null}{selected.estado === "confirmada" ? <button className="button primary" onClick={() => void changeStatus("atendida")}>Marcar atendida</button> : null}</div> : null}</>}</section>
    </div>
    {appointmentModal ? <Modal title="Nueva cita" close={() => setAppointmentModal(false)}><form className="space-y-4" onSubmit={createAppointment}><div className="grid gap-3 sm:grid-cols-2"><Field label="Cliente"><select required className="form-control" value={form.cliente_id} onChange={(event) => setForm({ ...form, cliente_id: event.target.value, vehiculo_id: "" })}><option value="">Seleccionar cliente</option>{clients.map((client) => <option key={client.id} value={client.id}>{client.nombre}</option>)}</select></Field><Field label="Vehículo"><select required disabled={!form.cliente_id} className="form-control" value={form.vehiculo_id} onChange={(event) => setForm({ ...form, vehiculo_id: event.target.value })}><option value="">Seleccionar vehículo</option>{availableVehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.placa} · {vehicle.descripcion}</option>)}</select></Field><Field label="Inicio"><input required type="time" className="form-control" value={form.inicio} onChange={(event) => setForm({ ...form, inicio: event.target.value })} /></Field><Field label="Fin"><input required type="time" className="form-control" value={form.fin} onChange={(event) => setForm({ ...form, fin: event.target.value })} /></Field><Field label="Bahía"><select className="form-control" value={form.bahia_id} onChange={(event) => setForm({ ...form, bahia_id: event.target.value })}><option value="">Sin asignar</option>{activeBays.map((bay) => <option key={bay.id} value={bay.id}>{bay.codigo} · {bay.nombre}</option>)}</select></Field><Field label="Mecánico"><select className="form-control" value={form.empleado_id} onChange={(event) => setForm({ ...form, empleado_id: event.target.value })}><option value="">Sin asignar</option>{availableEmployees.map((employee) => <option key={employee.id} value={employee.id}>{employee.nombre}</option>)}</select></Field></div><Field label="Motivo"><input required minLength={3} className="form-control" value={form.motivo} onChange={(event) => setForm({ ...form, motivo: event.target.value })} /></Field><Field label="Observaciones"><textarea className="form-control min-h-20" value={form.observaciones} onChange={(event) => setForm({ ...form, observaciones: event.target.value })} /></Field><Actions saving={saving} close={() => setAppointmentModal(false)} label="Programar cita" /></form></Modal> : null}
    {bayModal ? <Modal title="Nueva bahía de trabajo" close={() => setBayModal(false)}><div className="mb-5 grid gap-2 sm:grid-cols-2">{bays.map((bay) => <div key={bay.id} className="rounded-xl border bg-slate-50 p-3"><div className="flex justify-between"><strong>{bay.codigo}</strong><StatusBadge status={bay.estado} label={bay.estado === "activo" ? "Activa" : bay.estado} /></div><div className="mt-1 text-sm">{bay.nombre}</div></div>)}</div><form className="space-y-4 border-t pt-5" onSubmit={createBay}><div className="grid gap-3 sm:grid-cols-2"><Field label="Código"><input required className="form-control uppercase" value={bayForm.codigo} onChange={(event) => setBayForm({ ...bayForm, codigo: event.target.value })} /></Field><Field label="Nombre"><input required className="form-control" value={bayForm.nombre} onChange={(event) => setBayForm({ ...bayForm, nombre: event.target.value })} /></Field></div><Field label="Descripción"><textarea className="form-control min-h-20" value={bayForm.descripcion} onChange={(event) => setBayForm({ ...bayForm, descripcion: event.target.value })} /></Field><Actions saving={saving} close={() => setBayModal(false)} label="Crear bahía" /></form></Modal> : null}
  </div>;
}

function Metric({ label, value }: { label: string; value: number }) { return <div className="rounded-xl border bg-white p-4 shadow-sm"><div className="text-2xl font-black text-slate-900">{value}</div><div className="text-xs text-slate-500">{label}</div></div>; }
function Info({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="flex gap-3"><span className="text-blue-600">{icon}</span><div><div className="text-[10px] font-bold uppercase text-slate-400">{label}</div><div className="text-sm font-semibold">{value}</div></div></div>; }
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Actions({ saving, close, label }: { saving: boolean; close: () => void; label: string }) { return <div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={close}>Cancelar</button><button disabled={saving} className="button primary">{saving ? "Guardando…" : label}</button></div>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex justify-between border-b bg-white px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
