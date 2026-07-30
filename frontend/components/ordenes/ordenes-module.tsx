"use client";

import {
  CalendarClock,
  Camera,
  Car,
  ChevronRight,
  ClipboardList,
  ClipboardCheck,
  Gauge,
  Pencil,
  Plus,
  Search,
  UserRound,
  UsersRound,
  Wrench,
  History,
  X,
} from "lucide-react";
import Image from "next/image";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiError, apiRequest } from "@/lib/api";
import type { Cliente, OrdenTrabajo, Vehiculo } from "@/types";

type Branch = { id: string; nombre: string; es_principal: boolean };
type Employee = { id: string; nombres: string; apellidos: string; cargo: string; especialidad: string | null };
type Assignment = { id: string; empleado_id: string; empleado_nombre: string; cargo: string; es_responsable: boolean };
type InspectionFile = { id: string; nombre_original: string; url: string | null };
type Inspection = { id: string; tipo: string; confirmada_at: string | null; created_at: string; archivos: InspectionFile[] };
type OrderService = { id:string; descripcion:string; cantidad:string; total:string; estado:string };
type OrderHistory = { id:string; estado_anterior:string|null; estado_nuevo:string; motivo:string|null; usuario_nombre:string; created_at:string };
type Options = { sucursales: Branch[] };
type OrderForm = {
  sucursal_id: string;
  cliente_id: string;
  vehiculo_id: string;
  kilometraje: string;
  nivel_combustible: string;
  falla_reportada: string;
  observaciones: string;
  fecha_estimada_entrega: string;
};

const states = [
  "recepcion",
  "diagnostico",
  "esperando_aprobacion",
  "aprobada",
  "en_proceso",
  "terminada",
  "entregada",
  "cancelada",
] as const;

const labels: Record<string, string> = {
  borrador: "Borrador",
  recepcion: "Recepción",
  diagnostico: "Diagnóstico",
  esperando_aprobacion: "Esperando aprobación",
  aprobada: "Aprobada",
  en_proceso: "En proceso",
  terminada: "Terminada",
  entregada: "Entregada",
  cancelada: "Cancelada",
};

const nextStates: Record<string, string[]> = {
  borrador: ["recepcion", "cancelada"],
  recepcion: ["diagnostico", "cancelada"],
  diagnostico: ["cancelada"],
  esperando_aprobacion: ["aprobada", "cancelada"],
  aprobada: ["en_proceso", "cancelada"],
  en_proceso: ["terminada", "cancelada"],
  terminada: ["entregada", "en_proceso"],
};

function displayClient(client: Cliente) {
  return client.razon_social || `${client.nombres || ""} ${client.apellidos || ""}`.trim();
}

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "Ocurrió un error inesperado";
}

export function OrdenesModule() {
  const [orders, setOrders] = useState<OrdenTrabajo[]>([]);
  const [clients, setClients] = useState<Cliente[]>([]);
  const [vehicles, setVehicles] = useState<Vehiculo[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [orderServices, setOrderServices] = useState<OrderService[]>([]);
  const [orderHistory, setOrderHistory] = useState<OrderHistory[]>([]);
  const [employeeId, setEmployeeId] = useState("");
  const [selected, setSelected] = useState<OrdenTrabajo | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [modal, setModal] = useState(false);
  const [editModal, setEditModal] = useState(false);
  const [form, setForm] = useState<OrderForm>({
    sucursal_id: "",
    cliente_id: "",
    vehiculo_id: "",
    kilometraje: "",
    nivel_combustible: "50",
    falla_reportada: "",
    observaciones: "",
    fecha_estimada_entrega: "",
  });
  const [edit, setEdit] = useState({ diagnostico: "", observaciones: "", fecha_estimada_entrega: "" });

  const loadOrders = useCallback(async (term = "", state = "") => {
    setLoading(true);
    try {
      const query = new URLSearchParams();
      if (term.trim()) query.set("search", term.trim());
      if (state) query.set("estado", state);
      const data = await apiRequest<OrdenTrabajo[]>(`/ordenes?${query.toString()}`);
      setOrders(data);
      setSelected((current) => current ? data.find((order) => order.id === current.id) || current : null);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => void loadOrders(search, filter), 300);
    return () => window.clearTimeout(timeout);
  }, [search, filter, loadOrders]);

  useEffect(() => {
    const timeout = window.setTimeout(async () => {
      try {
        const [clientData, optionData] = await Promise.all([
          apiRequest<Cliente[]>("/clientes?limit=100"),
          apiRequest<Options>("/ordenes/opciones"),
        ]);
        setClients(clientData);
        setBranches(optionData.sucursales);
        setForm((current) => ({
          ...current,
          sucursal_id: current.sucursal_id || optionData.sucursales[0]?.id || "",
        }));
      } catch (requestError) {
        setError(errorMessage(requestError));
      }
    }, 0);
    return () => window.clearTimeout(timeout);
  }, []);

  const stats = useMemo(() => ({
    active: orders.filter((order) => !["entregada", "cancelada"].includes(order.estado)).length,
    waiting: orders.filter((order) => order.estado === "esperando_aprobacion").length,
    ready: orders.filter((order) => order.estado === "terminada").length,
  }), [orders]);

  async function selectClient(clientId: string) {
    setForm((current) => ({ ...current, cliente_id: clientId, vehiculo_id: "" }));
    if (!clientId) return setVehicles([]);
    try {
      setVehicles(await apiRequest<Vehiculo[]>(`/clientes/${clientId}/vehiculos`));
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }

  async function selectOrder(order: OrdenTrabajo) {
    setSelected(order);
    setEmployeeId("");
    try {
      const [staff, assigned, inspectionData, serviceData, historyData] = await Promise.all([
        apiRequest<Employee[]>(`/empleados?sucursal_id=${order.sucursal_id}`),
        apiRequest<Assignment[]>(`/empleados/asignaciones/orden/${order.id}`),
        apiRequest<Inspection[]>(`/inspecciones/orden/${order.id}`),
        apiRequest<OrderService[]>(`/ordenes/${order.id}/servicios`),
        apiRequest<OrderHistory[]>(`/ordenes/${order.id}/historial`),
      ]);
      setEmployees(staff);
      setAssignments(assigned);
      setInspections(inspectionData);
      setOrderServices(serviceData);
      setOrderHistory(historyData);
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }

  async function assignEmployee() {
    if (!selected || !employeeId) return;
    setSaving(true);
    try {
      await apiRequest<Assignment>("/empleados/asignaciones", {
        method: "POST",
        body: JSON.stringify({
          orden_id: selected.id,
          empleado_id: employeeId,
          es_responsable: assignments.length === 0,
        }),
      });
      setAssignments(await apiRequest<Assignment[]>(`/empleados/asignaciones/orden/${selected.id}`));
      setEmployeeId("");
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function removeAssignment(assignmentId: string) {
    if (!selected) return;
    try {
      await apiRequest<void>(`/empleados/asignaciones/${assignmentId}`, { method: "DELETE" });
      setAssignments(await apiRequest<Assignment[]>(`/empleados/asignaciones/orden/${selected.id}`));
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }

  async function updateService(serviceId: string, estado: string) {
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await apiRequest<OrderService>(
        `/ordenes/${selected.id}/servicios/${serviceId}`,
        { method: "PATCH", body: JSON.stringify({ estado }) },
      );
      setOrderServices((current) =>
        current.map((item) => item.id === updated.id ? updated : item),
      );
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  function openNew() {
    setForm({
      sucursal_id: branches[0]?.id || "",
      cliente_id: "",
      vehiculo_id: "",
      kilometraje: "",
      nivel_combustible: "50",
      falla_reportada: "",
      observaciones: "",
      fecha_estimada_entrega: "",
    });
    setVehicles([]);
    setModal(true);
  }

  async function createOrder(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const order = await apiRequest<OrdenTrabajo>("/ordenes", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          kilometraje: form.kilometraje ? Number(form.kilometraje) : null,
          nivel_combustible: form.nivel_combustible ? Number(form.nivel_combustible) : null,
          fecha_estimada_entrega: form.fecha_estimada_entrega
            ? new Date(form.fecha_estimada_entrega).toISOString()
            : null,
        }),
      });
      setModal(false);
      await loadOrders(search, filter);
      await selectOrder(order);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  function openEdit(order: OrdenTrabajo) {
    setEdit({
      diagnostico: order.diagnostico || "",
      observaciones: order.observaciones || "",
      fecha_estimada_entrega: order.fecha_estimada_entrega
        ? order.fecha_estimada_entrega.slice(0, 16)
        : "",
    });
    setEditModal(true);
  }

  async function updateOrder(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await apiRequest<OrdenTrabajo>(`/ordenes/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          ...edit,
          fecha_estimada_entrega: edit.fecha_estimada_entrega
            ? new Date(edit.fecha_estimada_entrega).toISOString()
            : null,
        }),
      });
      setSelected(updated);
      setEditModal(false);
      await loadOrders(search, filter);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(state: string) {
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await apiRequest<OrdenTrabajo>(`/ordenes/${selected.id}/estado`, {
        method: "PATCH",
        body: JSON.stringify({ estado: state }),
      });
      setSelected(updated);
      await selectOrder(updated);
      await loadOrders(search, filter);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <PageHeading
        title="Órdenes de trabajo"
        subtitle="Recepción, diagnóstico, reparación y entrega del vehículo."
        action={<button className="button primary" onClick={openNew}><Plus size={16} /> Nueva orden</button>}
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <Metric icon={<ClipboardList size={19} />} label="Órdenes activas" value={stats.active} />
        <Metric icon={<CalendarClock size={19} />} label="Esperando aprobación" value={stats.waiting} />
        <Metric icon={<Car size={19} />} label="Listas para entregar" value={stats.ready} />
      </div>

      {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm sm:flex-row">
        <label className="flex flex-1 items-center gap-2 rounded-lg bg-slate-50 px-3">
          <Search size={17} className="text-slate-400" />
          <input className="h-10 w-full bg-transparent text-sm outline-none" placeholder="Placa, cliente, documento o falla" value={search} onChange={(event) => setSearch(event.target.value)} />
        </label>
        <select className="form-control sm:max-w-56" value={filter} onChange={(event) => setFilter(event.target.value)}>
          <option value="">Todos los estados</option>
          {states.map((state) => <option key={state} value={state}>{labels[state]}</option>)}
        </select>
      </div>

      <div className="grid min-h-[570px] gap-4 xl:grid-cols-[1fr_1.15fr]">
        <section className="space-y-3">
          {loading ? <Empty text="Cargando órdenes…" /> : orders.length === 0 ? <Empty text="No hay órdenes con estos filtros." /> : orders.map((order) => (
            <button key={order.id} onClick={() => void selectOrder(order)} className={`w-full rounded-xl border bg-white p-4 text-left shadow-sm transition ${selected?.id === order.id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200 hover:border-slate-300"}`}>
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="rounded-md bg-slate-900 px-2 py-1 font-mono text-xs font-bold text-white">OT-{String(order.numero).padStart(5, "0")}</span>
                  <span className="rounded-md bg-slate-100 px-2 py-1 font-mono text-xs font-bold text-slate-700">{order.vehiculo_placa}</span>
                </div>
                <StatusBadge status={order.estado} label={labels[order.estado]} />
              </div>
              <h3 className="mt-3 font-semibold text-slate-950">{order.cliente_nombre}</h3>
              <p className="mt-1 line-clamp-2 text-sm text-slate-500">{order.falla_reportada || "Sin falla registrada"}</p>
              <div className="mt-3 flex items-center justify-between text-xs text-slate-400"><span>{order.sucursal_nombre}</span><span>{new Date(order.fecha_recepcion).toLocaleDateString("es-PE")}</span></div>
            </button>
          ))}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          {!selected ? <div className="flex h-full min-h-96 flex-col items-center justify-center text-center"><span className="mb-4 rounded-2xl bg-blue-50 p-4 text-blue-600"><ClipboardList size={30} /></span><h2 className="font-semibold">Selecciona una orden</h2><p className="mt-1 text-sm text-slate-500">Consulta su recepción y avanza el trabajo.</p></div> : (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-5">
                <div><div className="flex items-center gap-2"><h2 className="text-xl font-bold">OT-{String(selected.numero).padStart(5, "0")}</h2><StatusBadge status={selected.estado} label={labels[selected.estado]} /></div><p className="mt-1 text-sm text-slate-500">{selected.sucursal_nombre}</p></div>
                {!["entregada", "cancelada"].includes(selected.estado) ? <button className="button" onClick={() => openEdit(selected)}><Pencil size={15} /> Editar</button> : null}
              </div>
              <div className="grid gap-3 py-5 sm:grid-cols-2">
                <Info icon={<UserRound size={16} />} label="Cliente" value={selected.cliente_nombre} detail={selected.cliente_documento} />
                <Info icon={<Car size={16} />} label="Vehículo" value={selected.vehiculo_placa} detail={selected.vehiculo_descripcion} />
                <Info icon={<Gauge size={16} />} label="Kilometraje" value={selected.kilometraje ? `${selected.kilometraje.toLocaleString("es-PE")} km` : "No registrado"} detail={`Combustible: ${selected.nivel_combustible ?? "—"}%`} />
                <Info icon={<CalendarClock size={16} />} label="Entrega estimada" value={selected.fecha_estimada_entrega ? new Date(selected.fecha_estimada_entrega).toLocaleString("es-PE") : "Por definir"} />
              </div>
              <div className="rounded-xl bg-slate-50 p-4"><span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Falla reportada</span><p className="mt-2 text-sm leading-6 text-slate-700">{selected.falla_reportada || "Sin información"}</p></div>
              {selected.diagnostico ? <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50 p-4"><span className="text-[10px] font-bold uppercase tracking-wide text-blue-500">Diagnóstico</span><p className="mt-2 text-sm leading-6 text-slate-700">{selected.diagnostico}</p></div> : null}
              <div className="mt-5 border-t border-slate-100 pt-5">
                <div className="mb-3 flex items-center gap-2"><Wrench size={16} className="text-blue-600" /><h3 className="text-sm font-semibold">Servicios aprobados</h3></div>
                {orderServices.length ? <div className="space-y-2">{orderServices.map((service) => <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 p-3" key={service.id}><div><div className="text-sm font-semibold">{service.descripcion}</div><div className="text-xs text-slate-500">{Number(service.cantidad)} unidad(es) · S/ {Number(service.total).toFixed(2)}</div></div><select className="form-control max-w-40 capitalize" disabled={saving || !["aprobada", "en_proceso", "terminada"].includes(selected.estado)} value={service.estado} onChange={(event) => void updateService(service.id, event.target.value)}><option value="pendiente">Pendiente</option><option value="en_proceso">En proceso</option><option value="terminado">Terminado</option><option value="cancelado">Cancelado</option></select></div>)}</div> : <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">Los servicios aparecerán cuando se apruebe la cotización.</p>}
              </div>
              <div className="mt-5 border-t border-slate-100 pt-5">
                <div className="mb-3 flex items-center gap-2"><ClipboardCheck size={16} className="text-blue-600" /><h3 className="text-sm font-semibold">Inspecciones y fotografías</h3></div>
                {inspections.length === 0 ? <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">Esta OT todavía no tiene inspecciones. No se podrá enviar ni aprobar una cotización.</p> : <div className="space-y-3">{inspections.map((inspection) => <div key={inspection.id} className="rounded-xl bg-slate-50 p-3"><div className="flex justify-between"><strong className="flex items-center gap-2 text-sm capitalize">{inspection.tipo}</strong><span className={`text-xs font-bold ${inspection.confirmada_at ? "text-emerald-600" : "text-orange-600"}`}>{inspection.confirmada_at ? "Confirmada" : "Borrador"}</span></div><div className="mt-3 grid grid-cols-3 gap-2">{inspection.archivos.length === 0 ? <span className="col-span-full flex items-center gap-1 text-xs text-slate-500"><Camera size={13} /> Sin fotografías</span> : inspection.archivos.map((file) => file.url ? <a key={file.id} href={file.url} target="_blank" rel="noreferrer" className="overflow-hidden rounded-lg border bg-white"><Image loader={({ src }) => src} unoptimized src={file.url} alt={file.nombre_original} width={180} height={110} className="h-20 w-full object-cover" /></a> : null)}</div></div>)}</div>}
              </div>
              <div className="mt-5 border-t border-slate-100 pt-5">
                <div className="mb-3 flex items-center gap-2"><UsersRound size={16} className="text-blue-600" /><h3 className="text-sm font-semibold">Equipo asignado</h3></div>
                {assignments.length ? <div className="mb-3 flex flex-wrap gap-2">{assignments.map((assignment) => <span key={assignment.id} className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700">{assignment.empleado_nombre}{assignment.es_responsable ? <strong className="text-blue-600">Responsable</strong> : null}<button className="text-slate-400 hover:text-red-600" onClick={() => void removeAssignment(assignment.id)}><X size={13} /></button></span>)}</div> : <p className="mb-3 text-xs text-slate-500">Aún no hay empleados asignados.</p>}
                {["aprobada", "en_proceso"].includes(selected.estado) ? <div className="flex gap-2"><select className="form-control" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}><option value="">Seleccionar empleado</option>{employees.filter((employee) => !assignments.some((assignment) => assignment.empleado_id === employee.id)).map((employee) => <option key={employee.id} value={employee.id}>{employee.nombres} {employee.apellidos} · {employee.cargo}</option>)}</select><button disabled={!employeeId || saving} className="button primary shrink-0" onClick={() => void assignEmployee()}>Asignar</button></div> : <p className="text-xs text-amber-700">La OT debe estar aprobada para asignar personal.</p>}
              </div>
              <div className="mt-5 grid grid-cols-3 gap-3 border-t border-slate-100 pt-5">
                <Total label="Subtotal" value={selected.total} />
                <Total label="Total" value={selected.total} />
                <Total label="Saldo" value={selected.saldo} strong />
              </div>
              {(nextStates[selected.estado] || []).length ? <div className="mt-5 border-t border-slate-100 pt-5"><h3 className="mb-3 text-sm font-semibold">Siguiente etapa</h3><div className="flex flex-wrap gap-2">{nextStates[selected.estado].map((state) => <button key={state} disabled={saving} onClick={() => void changeStatus(state)} className={`button ${state === "cancelada" ? "text-red-600" : "primary"}`}>{labels[state]} <ChevronRight size={14} /></button>)}</div></div> : null}
              <div className="mt-5 border-t border-slate-100 pt-5"><div className="mb-3 flex items-center gap-2"><History size={16} className="text-blue-600" /><h3 className="text-sm font-semibold">Historial de la orden</h3></div><div className="space-y-3">{orderHistory.map((item) => <div className="border-l-2 border-blue-200 pl-3" key={item.id}><div className="text-sm font-semibold">{item.estado_anterior ? `${labels[item.estado_anterior] || item.estado_anterior} → ` : ""}{labels[item.estado_nuevo] || item.estado_nuevo}</div><div className="text-xs text-slate-500">{item.usuario_nombre} · {new Date(item.created_at).toLocaleString("es-PE")}</div>{item.motivo ? <div className="text-xs text-slate-400">{item.motivo}</div> : null}</div>)}</div></div>
            </>
          )}
        </section>
      </div>

      {modal ? <Modal title="Nueva orden de trabajo" close={() => setModal(false)}><form className="space-y-4" onSubmit={createOrder}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Sucursal"><select required className="form-control" value={form.sucursal_id} onChange={(e) => setForm({ ...form, sucursal_id: e.target.value })}><option value="">Seleccionar</option>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.nombre}</option>)}</select></Field>
          <Field label="Cliente"><select required className="form-control" value={form.cliente_id} onChange={(e) => void selectClient(e.target.value)}><option value="">Seleccionar</option>{clients.map((client) => <option key={client.id} value={client.id}>{displayClient(client)} · {client.numero_documento}</option>)}</select></Field>
          <Field label="Vehículo"><select required disabled={!form.cliente_id} className="form-control" value={form.vehiculo_id} onChange={(e) => setForm({ ...form, vehiculo_id: e.target.value })}><option value="">Seleccionar</option>{vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.placa} · {vehicle.marca} {vehicle.modelo}</option>)}</select></Field>
          <Field label="Kilometraje"><input type="number" min="0" className="form-control" value={form.kilometraje} onChange={(e) => setForm({ ...form, kilometraje: e.target.value })} /></Field>
          <Field label={`Nivel de combustible (${form.nivel_combustible}%)`}><input type="range" min="0" max="100" step="5" className="h-11 w-full" value={form.nivel_combustible} onChange={(e) => setForm({ ...form, nivel_combustible: e.target.value })} /></Field>
          <Field label="Entrega estimada"><input type="datetime-local" className="form-control" value={form.fecha_estimada_entrega} onChange={(e) => setForm({ ...form, fecha_estimada_entrega: e.target.value })} /></Field>
        </div>
        <Field label="Falla reportada"><textarea required minLength={3} className="form-control min-h-24 resize-y" value={form.falla_reportada} onChange={(e) => setForm({ ...form, falla_reportada: e.target.value })} /></Field>
        <Field label="Observaciones de recepción"><textarea className="form-control min-h-20 resize-y" value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} /></Field>
        <Actions saving={saving} cancel={() => setModal(false)} />
      </form></Modal> : null}

      {editModal && selected ? <Modal title={`Actualizar OT-${String(selected.numero).padStart(5, "0")}`} close={() => setEditModal(false)}><form className="space-y-4" onSubmit={updateOrder}>
        <Field label="Diagnóstico"><textarea className="form-control min-h-28 resize-y" value={edit.diagnostico} onChange={(e) => setEdit({ ...edit, diagnostico: e.target.value })} /></Field>
        <Field label="Observaciones"><textarea className="form-control min-h-20 resize-y" value={edit.observaciones} onChange={(e) => setEdit({ ...edit, observaciones: e.target.value })} /></Field>
        <Field label="Entrega estimada"><input type="datetime-local" className="form-control" value={edit.fecha_estimada_entrega} onChange={(e) => setEdit({ ...edit, fecha_estimada_entrega: e.target.value })} /></Field>
        <Actions saving={saving} cancel={() => setEditModal(false)} />
      </form></Modal> : null}
    </div>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><span className="rounded-xl bg-blue-50 p-2.5 text-blue-600">{icon}</span><div><div className="text-2xl font-bold">{value}</div><div className="text-xs text-slate-500">{label}</div></div></div>;
}
function Info({ icon, label, value, detail }: { icon: React.ReactNode; label: string; value: string; detail?: string }) {
  return <div className="flex gap-3 rounded-xl bg-slate-50 p-3"><span className="mt-0.5 text-slate-400">{icon}</span><div className="min-w-0"><div className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</div><div className="truncate text-sm font-semibold text-slate-800">{value}</div>{detail ? <div className="truncate text-xs text-slate-500">{detail}</div> : null}</div></div>;
}
function Total({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return <div><div className="text-[10px] font-bold uppercase text-slate-400">{label}</div><div className={`mt-1 ${strong ? "text-lg font-bold text-blue-700" : "text-sm font-semibold"}`}>S/ {Number(value).toFixed(2)}</div></div>;
}
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex justify-between border-b border-slate-100 bg-white px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
function Actions({ saving, cancel }: { saving: boolean; cancel: () => void }) { return <div className="flex justify-end gap-2 border-t border-slate-100 pt-4"><button type="button" className="button" onClick={cancel}>Cancelar</button><button disabled={saving} className="button primary">{saving ? "Guardando…" : "Guardar orden"}</button></div>; }
