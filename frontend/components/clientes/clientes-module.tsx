"use client";

import {
  Building2,
  Car,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Plus,
  Search,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";
import type { Cliente, Vehiculo } from "@/types";

type ClientForm = {
  tipo_persona: "natural" | "juridica";
  tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellidos: string;
  razon_social: string;
  telefono: string;
  email: string;
  direccion: string;
  observaciones: string;
  autoriza_contacto: boolean;
};

type VehicleForm = {
  placa: string;
  marca: string;
  modelo: string;
  anio: string;
  color: string;
  combustible: string;
  vin: string;
  motor: string;
  cilindrada: string;
};

const emptyClient: ClientForm = {
  tipo_persona: "natural",
  tipo_documento: "DNI",
  numero_documento: "",
  nombres: "",
  apellidos: "",
  razon_social: "",
  telefono: "",
  email: "",
  direccion: "",
  observaciones: "",
  autoriza_contacto: false,
};

const emptyVehicle: VehicleForm = {
  placa: "",
  marca: "",
  modelo: "",
  anio: "",
  color: "",
  combustible: "",
  vin: "",
  motor: "",
  cilindrada: "",
};

function clientName(client: Cliente) {
  return client.tipo_persona === "juridica"
    ? client.razon_social || "Empresa sin nombre"
    : `${client.nombres || ""} ${client.apellidos || ""}`.trim() || "Cliente sin nombre";
}

function initials(client: Cliente) {
  return clientName(client)
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

function messageFrom(error: unknown) {
  return error instanceof ApiError ? error.message : "Ocurrió un error inesperado";
}

export function ClientesModule() {
  const [clients, setClients] = useState<Cliente[]>([]);
  const [vehicles, setVehicles] = useState<Vehiculo[]>([]);
  const [selected, setSelected] = useState<Cliente | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [vehicleLoading, setVehicleLoading] = useState(false);
  const [error, setError] = useState("");
  const [clientModal, setClientModal] = useState(false);
  const [vehicleModal, setVehicleModal] = useState(false);
  const [editingClient, setEditingClient] = useState<Cliente | null>(null);
  const [editingVehicle, setEditingVehicle] = useState<Vehiculo | null>(null);
  const [clientForm, setClientForm] = useState<ClientForm>(emptyClient);
  const [vehicleForm, setVehicleForm] = useState<VehicleForm>(emptyVehicle);
  const [saving, setSaving] = useState(false);

  const loadClients = useCallback(async (term = "") => {
    setLoading(true);
    setError("");
    try {
      const query = term.trim() ? `?search=${encodeURIComponent(term.trim())}` : "";
      const data = await apiRequest<Cliente[]>(`/clientes${query}`);
      setClients(data);
      setSelected((current) =>
        current ? data.find((client) => client.id === current.id) || null : null,
      );
    } catch (requestError) {
      setError(messageFrom(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadVehicles = useCallback(async (clientId: string) => {
    setVehicleLoading(true);
    try {
      setVehicles(await apiRequest<Vehiculo[]>(`/clientes/${clientId}/vehiculos`));
    } catch (requestError) {
      setError(messageFrom(requestError));
    } finally {
      setVehicleLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => void loadClients(search), 300);
    return () => window.clearTimeout(timeout);
  }, [search, loadClients]);

  const stats = useMemo(
    () => ({
      people: clients.filter((client) => client.tipo_persona === "natural").length,
      companies: clients.filter((client) => client.tipo_persona === "juridica").length,
    }),
    [clients],
  );

  function openNewClient() {
    setEditingClient(null);
    setClientForm(emptyClient);
    setClientModal(true);
  }

  function selectClient(client: Cliente) {
    setSelected(client);
    void loadVehicles(client.id);
  }

  function openEditClient(client: Cliente) {
    setEditingClient(client);
    setClientForm({
      tipo_persona: client.tipo_persona,
      tipo_documento: client.tipo_documento,
      numero_documento: client.numero_documento,
      nombres: client.nombres || "",
      apellidos: client.apellidos || "",
      razon_social: client.razon_social || "",
      telefono: client.telefono || "",
      email: client.email || "",
      direccion: client.direccion || "",
      observaciones: client.observaciones || "",
      autoriza_contacto: client.autoriza_contacto,
    });
    setClientModal(true);
  }

  function openNewVehicle() {
    setEditingVehicle(null);
    setVehicleForm(emptyVehicle);
    setVehicleModal(true);
  }

  function openEditVehicle(vehicle: Vehiculo) {
    setEditingVehicle(vehicle);
    setVehicleForm({
      placa: vehicle.placa,
      marca: vehicle.marca || "",
      modelo: vehicle.modelo || "",
      anio: vehicle.anio?.toString() || "",
      color: vehicle.color || "",
      combustible: vehicle.combustible || "",
      vin: vehicle.vin || "",
      motor: vehicle.motor || "",
      cilindrada: vehicle.cilindrada || "",
    });
    setVehicleModal(true);
  }

  async function saveClient(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const saved = await apiRequest<Cliente>(
        editingClient ? `/clientes/${editingClient.id}` : "/clientes",
        {
          method: editingClient ? "PATCH" : "POST",
          body: JSON.stringify(clientForm),
        },
      );
      setClientModal(false);
      await loadClients(search);
      setSelected(saved);
      await loadVehicles(saved.id);
    } catch (requestError) {
      setError(messageFrom(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function saveVehicle(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setSaving(true);
    setError("");
    const payload = {
      ...vehicleForm,
      anio: vehicleForm.anio ? Number(vehicleForm.anio) : null,
    };
    try {
      await apiRequest<Vehiculo>(
        editingVehicle
          ? `/vehiculos/${editingVehicle.id}`
          : `/clientes/${selected.id}/vehiculos`,
        {
          method: editingVehicle ? "PATCH" : "POST",
          body: JSON.stringify(payload),
        },
      );
      setVehicleModal(false);
      await loadVehicles(selected.id);
    } catch (requestError) {
      setError(messageFrom(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function deactivateClient(client: Cliente) {
    if (!window.confirm(`¿Desactivar a ${clientName(client)}?`)) return;
    try {
      await apiRequest<void>(`/clientes/${client.id}`, { method: "DELETE" });
      if (selected?.id === client.id) setSelected(null);
      await loadClients(search);
    } catch (requestError) {
      setError(messageFrom(requestError));
    }
  }

  async function deactivateVehicle(vehicle: Vehiculo) {
    if (!selected || !window.confirm(`¿Desactivar el vehículo ${vehicle.placa}?`)) return;
    try {
      await apiRequest<void>(`/vehiculos/${vehicle.id}`, { method: "DELETE" });
      await loadVehicles(selected.id);
    } catch (requestError) {
      setError(messageFrom(requestError));
    }
  }

  return (
    <div className="space-y-5">
      <PageHeading
        title="Clientes y vehículos"
        subtitle="Administra propietarios y su historial vehicular desde un solo lugar."
        action={
          <button className="button primary" onClick={openNewClient}>
            <Plus size={16} /> Nuevo cliente
          </button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat icon={<UserRound size={19} />} label="Personas" value={stats.people} />
        <Stat icon={<Building2 size={19} />} label="Empresas" value={stats.companies} />
        <Stat icon={<Car size={19} />} label="Vehículos seleccionados" value={vehicles.length} />
      </div>

      {error ? (
        <div className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
          <button onClick={() => setError("")} aria-label="Cerrar error"><X size={16} /></button>
        </div>
      ) : null}

      <div className="grid min-h-[560px] gap-4 xl:grid-cols-[minmax(360px,0.9fr)_minmax(480px,1.3fr)]">
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 p-4">
            <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3">
              <Search size={17} className="text-slate-400" />
              <input
                className="h-11 w-full bg-transparent text-sm outline-none"
                placeholder="Nombre, documento, teléfono o correo"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
          </div>
          <div className="max-h-[650px] overflow-y-auto p-2">
            {loading ? (
              <Empty text="Cargando clientes…" />
            ) : clients.length === 0 ? (
              <Empty text="No encontramos clientes. Registra el primero." />
            ) : (
              clients.map((client) => (
                <button
                  key={client.id}
                  onClick={() => selectClient(client)}
                  className={`mb-1 flex w-full items-center gap-3 rounded-xl p-3 text-left transition ${
                    selected?.id === client.id
                      ? "bg-blue-50 ring-1 ring-blue-200"
                      : "hover:bg-slate-50"
                  }`}
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">
                    {initials(client)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-slate-900">
                      {clientName(client)}
                    </span>
                    <span className="block truncate text-xs text-slate-500">
                      {client.tipo_documento} {client.numero_documento}
                      {client.telefono ? ` · ${client.telefono}` : ""}
                    </span>
                  </span>
                  {client.tipo_persona === "juridica" ? (
                    <Building2 size={16} className="text-slate-400" />
                  ) : (
                    <UserRound size={16} className="text-slate-400" />
                  )}
                </button>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          {!selected ? (
            <div className="flex h-full min-h-96 flex-col items-center justify-center text-center">
              <div className="mb-4 rounded-2xl bg-blue-50 p-4 text-blue-600"><UserRound size={30} /></div>
              <h2 className="font-semibold text-slate-900">Selecciona un cliente</h2>
              <p className="mt-1 max-w-xs text-sm text-slate-500">
                Aquí verás sus datos y los vehículos registrados.
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-5">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold text-slate-950">{clientName(selected)}</h2>
                    <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold uppercase text-emerald-700">
                      Activo
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">
                    {selected.tipo_documento} {selected.numero_documento}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button className="button" onClick={() => openEditClient(selected)}>
                    <Pencil size={15} /> Editar
                  </button>
                  <button className="button text-red-600" onClick={() => void deactivateClient(selected)}>
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              <div className="grid gap-3 py-5 sm:grid-cols-2">
                <Info icon={<Phone size={16} />} label="Teléfono" value={selected.telefono} />
                <Info icon={<Mail size={16} />} label="Correo" value={selected.email} />
                <Info icon={<MapPin size={16} />} label="Dirección" value={selected.direccion} wide />
              </div>

              <div className="flex items-center justify-between border-t border-slate-100 pt-5">
                <div>
                  <h3 className="font-semibold text-slate-900">Vehículos</h3>
                  <p className="text-xs text-slate-500">Vehículos actualmente vinculados</p>
                </div>
                <button className="button primary" onClick={openNewVehicle}>
                  <Plus size={15} /> Agregar
                </button>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {vehicleLoading ? (
                  <Empty text="Cargando vehículos…" />
                ) : vehicles.length === 0 ? (
                  <div className="col-span-full rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-500">
                    Este cliente aún no tiene vehículos.
                  </div>
                ) : (
                  vehicles.map((vehicle) => (
                    <article key={vehicle.id} className="rounded-xl border border-slate-200 p-4">
                      <div className="flex items-start justify-between gap-2">
                        <div className="rounded-lg bg-slate-900 px-2.5 py-1.5 font-mono text-sm font-bold tracking-wider text-white">
                          {vehicle.placa}
                        </div>
                        <div className="flex gap-1">
                          <button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" onClick={() => openEditVehicle(vehicle)}>
                            <Pencil size={14} />
                          </button>
                          <button className="rounded-lg p-2 text-red-500 hover:bg-red-50" onClick={() => void deactivateVehicle(vehicle)}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                      <div className="mt-3 font-semibold text-slate-900">
                        {[vehicle.marca, vehicle.modelo].filter(Boolean).join(" ") || "Vehículo"}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {[vehicle.anio, vehicle.color, vehicle.combustible].filter(Boolean).join(" · ") || "Sin detalles"}
                      </div>
                    </article>
                  ))
                )}
              </div>
            </>
          )}
        </section>
      </div>

      {clientModal ? (
        <Modal title={editingClient ? "Editar cliente" : "Nuevo cliente"} onClose={() => setClientModal(false)}>
          <form onSubmit={saveClient} className="space-y-4">
            <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1">
              {(["natural", "juridica"] as const).map((type) => (
                <button
                  type="button"
                  key={type}
                  onClick={() => setClientForm({ ...clientForm, tipo_persona: type })}
                  className={`rounded-lg px-3 py-2 text-sm font-semibold ${clientForm.tipo_persona === type ? "bg-white text-blue-700 shadow-sm" : "text-slate-500"}`}
                >
                  {type === "natural" ? "Persona" : "Empresa"}
                </button>
              ))}
            </div>
            <div className="grid gap-3 sm:grid-cols-[140px_1fr]">
              <Field label="Documento">
                <select className="form-control" value={clientForm.tipo_documento} onChange={(e) => setClientForm({ ...clientForm, tipo_documento: e.target.value })}>
                  <option>DNI</option><option>RUC</option><option>CE</option><option>PAS</option>
                </select>
              </Field>
              <Field label="Número"><input required className="form-control" value={clientForm.numero_documento} onChange={(e) => setClientForm({ ...clientForm, numero_documento: e.target.value })} /></Field>
            </div>
            {clientForm.tipo_persona === "natural" ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Nombres"><input required className="form-control" value={clientForm.nombres} onChange={(e) => setClientForm({ ...clientForm, nombres: e.target.value })} /></Field>
                <Field label="Apellidos"><input className="form-control" value={clientForm.apellidos} onChange={(e) => setClientForm({ ...clientForm, apellidos: e.target.value })} /></Field>
              </div>
            ) : (
              <Field label="Razón social"><input required className="form-control" value={clientForm.razon_social} onChange={(e) => setClientForm({ ...clientForm, razon_social: e.target.value })} /></Field>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Teléfono"><input className="form-control" value={clientForm.telefono} onChange={(e) => setClientForm({ ...clientForm, telefono: e.target.value })} /></Field>
              <Field label="Correo"><input type="email" className="form-control" value={clientForm.email} onChange={(e) => setClientForm({ ...clientForm, email: e.target.value })} /></Field>
            </div>
            <Field label="Dirección"><input className="form-control" value={clientForm.direccion} onChange={(e) => setClientForm({ ...clientForm, direccion: e.target.value })} /></Field>
            <Field label="Observaciones"><textarea className="form-control min-h-20 resize-y" value={clientForm.observaciones} onChange={(e) => setClientForm({ ...clientForm, observaciones: e.target.value })} /></Field>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={clientForm.autoriza_contacto} onChange={(e) => setClientForm({ ...clientForm, autoriza_contacto: e.target.checked })} />
              Autoriza recibir comunicaciones
            </label>
            <Actions saving={saving} onCancel={() => setClientModal(false)} />
          </form>
        </Modal>
      ) : null}

      {vehicleModal ? (
        <Modal title={editingVehicle ? "Editar vehículo" : "Agregar vehículo"} onClose={() => setVehicleModal(false)}>
          <form onSubmit={saveVehicle} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Placa"><input required className="form-control uppercase" value={vehicleForm.placa} onChange={(e) => setVehicleForm({ ...vehicleForm, placa: e.target.value })} /></Field>
              <Field label="Año"><input type="number" min="1900" max="2100" className="form-control" value={vehicleForm.anio} onChange={(e) => setVehicleForm({ ...vehicleForm, anio: e.target.value })} /></Field>
              <Field label="Marca"><input className="form-control" value={vehicleForm.marca} onChange={(e) => setVehicleForm({ ...vehicleForm, marca: e.target.value })} /></Field>
              <Field label="Modelo"><input className="form-control" value={vehicleForm.modelo} onChange={(e) => setVehicleForm({ ...vehicleForm, modelo: e.target.value })} /></Field>
              <Field label="Color"><input className="form-control" value={vehicleForm.color} onChange={(e) => setVehicleForm({ ...vehicleForm, color: e.target.value })} /></Field>
              <Field label="Combustible">
                <select className="form-control" value={vehicleForm.combustible} onChange={(e) => setVehicleForm({ ...vehicleForm, combustible: e.target.value })}>
                  <option value="">Seleccionar</option><option>Gasolina</option><option>Diésel</option><option>GLP</option><option>GNV</option><option>Híbrido</option><option>Eléctrico</option>
                </select>
              </Field>
              <Field label="Motor"><input className="form-control" value={vehicleForm.motor} onChange={(e) => setVehicleForm({ ...vehicleForm, motor: e.target.value })} /></Field>
              <Field label="Cilindrada"><input className="form-control" value={vehicleForm.cilindrada} onChange={(e) => setVehicleForm({ ...vehicleForm, cilindrada: e.target.value })} /></Field>
            </div>
            <Field label="VIN"><input className="form-control uppercase" maxLength={50} value={vehicleForm.vin} onChange={(e) => setVehicleForm({ ...vehicleForm, vin: e.target.value })} /></Field>
            <Actions saving={saving} onCancel={() => setVehicleModal(false)} />
          </form>
        </Modal>
      ) : null}
    </div>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><span className="rounded-xl bg-blue-50 p-2.5 text-blue-600">{icon}</span><span><span className="block text-2xl font-bold text-slate-950">{value}</span><span className="text-xs text-slate-500">{label}</span></span></div>;
}

function Info({ icon, label, value, wide = false }: { icon: React.ReactNode; label: string; value: string | null; wide?: boolean }) {
  return <div className={`flex gap-3 rounded-xl bg-slate-50 p-3 ${wide ? "sm:col-span-2" : ""}`}><span className="mt-0.5 text-slate-400">{icon}</span><span className="min-w-0"><span className="block text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</span><span className="block truncate text-sm text-slate-700">{value || "No registrado"}</span></span></div>;
}

function Empty({ text }: { text: string }) {
  return <div className="p-10 text-center text-sm text-slate-500">{text}</div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>;
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}><div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-100 bg-white px-6 py-4"><h2 className="text-lg font-bold text-slate-950">{title}</h2><button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" onClick={onClose}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>;
}

function Actions({ saving, onCancel }: { saving: boolean; onCancel: () => void }) {
  return <div className="flex justify-end gap-2 border-t border-slate-100 pt-4"><button type="button" className="button" onClick={onCancel}>Cancelar</button><button className="button primary" disabled={saving}>{saving ? "Guardando…" : "Guardar"}</button></div>;
}
