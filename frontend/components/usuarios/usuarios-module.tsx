"use client";

import { KeyRound, Pencil, Plus, ShieldCheck, UserCog, Users, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ApiError, apiRequest } from "@/lib/api";

type Role = { id: string; codigo: string; nombre: string; descripcion: string | null };
type Branch = { id: string; nombre: string; es_principal: boolean };
type User = { id: string; membresia_id: string; email: string; nombres: string; apellidos: string; telefono: string | null; rol_id: string; rol_codigo: string; rol_nombre: string; estado: string; ultimo_acceso_at: string | null; sucursal_ids: string[]; sucursal_nombres: string[]; created_at: string };
type Form = { email: string; password: string; nombres: string; apellidos: string; telefono: string; rol_id: string; sucursal_ids: string[]; estado: string };
const empty: Form = { email: "", password: "", nombres: "", apellidos: "", telefono: "", rol_id: "", sucursal_ids: [], estado: "activo" };
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Ocurrió un error inesperado";

export function UsuariosModule() {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selected, setSelected] = useState<User | null>(null);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState<Form>(empty);
  const [modal, setModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [userData, options, branchData] = await Promise.all([apiRequest<User[]>("/usuarios"), apiRequest<{ roles: Role[] }>("/usuarios/opciones"), apiRequest<Branch[]>("/sucursales")]);
      setUsers(userData); setRoles(options.roles); setBranches(branchData);
      setSelected((value) => value ? userData.find((user) => user.id === value.id) || null : null);
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  function openNew() { setEditing(null); setForm({ ...empty, rol_id: roles.find((role) => role.codigo === "recepcionista")?.id || roles[0]?.id || "", sucursal_ids: branches.length === 1 ? [branches[0].id] : [] }); setModal(true); }
  function openEdit(user: User) { setEditing(user); setForm({ email: user.email, password: "", nombres: user.nombres, apellidos: user.apellidos, telefono: user.telefono || "", rol_id: user.rol_id, sucursal_ids: user.sucursal_ids, estado: user.estado }); setModal(true); }
  function toggleBranch(id: string) { setForm((value) => ({ ...value, sucursal_ids: value.sucursal_ids.includes(id) ? value.sucursal_ids.filter((item) => item !== id) : [...value.sucursal_ids, id] })); }
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      if (editing) await apiRequest<User>(`/usuarios/${editing.id}`, { method: "PATCH", body: JSON.stringify({ nombres: form.nombres, apellidos: form.apellidos, telefono: form.telefono || null, rol_id: form.rol_id, sucursal_ids: form.sucursal_ids, estado: form.estado }) });
      else await apiRequest<User>("/usuarios", { method: "POST", body: JSON.stringify({ ...form, telefono: form.telefono || null }) });
      setModal(false); await load();
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setSaving(false); }
  }
  const active = users.filter((user) => user.estado === "activo").length;

  return <div className="space-y-5">
    <PageHeading title="Usuarios y accesos" subtitle="Administra el equipo, sus roles y las sucursales permitidas." action={<button className="button primary" onClick={openNew} disabled={roles.length === 0}><Plus size={16} /> Nuevo usuario</button>} />
    {error ? <div className="flex justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}<button onClick={() => setError("")}><X size={16} /></button></div> : null}
    <div className="grid gap-3 sm:grid-cols-3"><Metric icon={<Users size={19} />} label="Usuarios registrados" value={users.length} /><Metric icon={<ShieldCheck size={19} />} label="Accesos activos" value={active} /><Metric icon={<KeyRound size={19} />} label="Roles disponibles" value={roles.length} /></div>
    <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]"><section className="space-y-3">{loading ? <Empty text="Cargando usuarios…" /> : users.length === 0 ? <Empty text="No hay usuarios adicionales." /> : users.map((user) => <button key={user.id} onClick={() => setSelected(user)} className={`w-full rounded-xl border bg-white p-4 text-left shadow-sm ${selected?.id === user.id ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"}`}><div className="flex justify-between"><span className="font-semibold">{user.nombres} {user.apellidos}</span><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${user.estado === "activo" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>{user.estado}</span></div><div className="mt-1 text-sm text-slate-500">{user.email}</div><div className="mt-3 flex justify-between text-xs"><strong className="text-blue-700">{user.rol_nombre}</strong><span className="text-slate-400">{user.sucursal_nombres.length ? user.sucursal_nombres.join(", ") : "Todas / sin restricción"}</span></div></button>)}</section>
      <section className="rounded-2xl border bg-white p-5 shadow-sm">{!selected ? <div className="flex min-h-80 items-center justify-center text-sm text-slate-500"><UserCog className="mr-2 text-blue-600" />Selecciona un usuario</div> : <><div className="flex justify-between border-b pb-5"><div><h2 className="text-xl font-bold">{selected.nombres} {selected.apellidos}</h2><p className="text-sm text-slate-500">{selected.email}</p></div><button className="button" onClick={() => openEdit(selected)}><Pencil size={15} /> Editar</button></div><div className="grid gap-3 py-5 sm:grid-cols-2"><Info label="Rol" value={selected.rol_nombre} /><Info label="Estado" value={selected.estado} /><Info label="Teléfono" value={selected.telefono || "No registrado"} /><Info label="Último acceso" value={selected.ultimo_acceso_at ? new Date(selected.ultimo_acceso_at).toLocaleString("es-PE") : "Nunca"} /></div><div className="rounded-xl bg-slate-50 p-4"><div className="text-[10px] font-bold uppercase text-slate-400">Sucursales permitidas</div><div className="mt-2 text-sm font-semibold">{selected.sucursal_nombres.length ? selected.sucursal_nombres.join(", ") : "Sin restricción específica"}</div></div></>}</section></div>
    {modal ? <Modal title={editing ? "Editar acceso" : "Nuevo usuario"} close={() => setModal(false)}><form className="space-y-4" onSubmit={save}><div className="grid gap-3 sm:grid-cols-2"><Field label="Nombres"><input required className="form-control" value={form.nombres} onChange={(event) => setForm({ ...form, nombres: event.target.value })} /></Field><Field label="Apellidos"><input required className="form-control" value={form.apellidos} onChange={(event) => setForm({ ...form, apellidos: event.target.value })} /></Field><Field label="Correo"><input required disabled={Boolean(editing)} type="email" className="form-control" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></Field>{!editing ? <Field label="Contraseña inicial"><input required minLength={8} type="password" className="form-control" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></Field> : null}<Field label="Teléfono"><input className="form-control" value={form.telefono} onChange={(event) => setForm({ ...form, telefono: event.target.value })} /></Field><Field label="Rol"><select required className="form-control" value={form.rol_id} onChange={(event) => setForm({ ...form, rol_id: event.target.value })}><option value="">Seleccionar rol</option>{roles.map((role) => <option key={role.id} value={role.id}>{role.nombre}</option>)}</select></Field>{editing ? <Field label="Estado del acceso"><select className="form-control" value={form.estado} onChange={(event) => setForm({ ...form, estado: event.target.value })}><option value="activo">Activo</option><option value="suspendido">Suspendido</option><option value="inactivo">Inactivo</option></select></Field> : null}</div><div><div className="mb-2 text-xs font-semibold text-slate-600">Sucursales permitidas</div><div className="grid gap-2 sm:grid-cols-2">{branches.map((branch) => <label key={branch.id} className="flex items-center gap-2 rounded-xl border bg-slate-50 p-3 text-sm"><input type="checkbox" checked={form.sucursal_ids.includes(branch.id)} onChange={() => toggleBranch(branch.id)} />{branch.nombre}{branch.es_principal ? <span className="text-[10px] text-blue-600">Principal</span> : null}</label>)}</div><p className="mt-2 text-xs text-slate-400">Sin selección significa que no se aplica una restricción específica de sucursal.</p></div><div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button" onClick={() => setModal(false)}>Cancelar</button><button disabled={saving} className="button primary">{saving ? "Guardando…" : "Guardar usuario"}</button></div></form></Modal> : null}
  </div>;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) { return <div className="flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm"><span className="rounded-xl bg-blue-50 p-2.5 text-blue-600">{icon}</span><div><div className="text-xl font-bold">{value}</div><div className="text-xs text-slate-500">{label}</div></div></div>; }
function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-slate-50 p-3"><div className="text-[10px] font-bold uppercase text-slate-400">{label}</div><div className="mt-1 font-semibold capitalize">{value}</div></div>; }
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">{text}</div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex justify-between border-b bg-white px-6 py-4"><h2 className="text-lg font-bold">{title}</h2><button onClick={close}><X size={18} /></button></div><div className="p-6">{children}</div></div></div>; }
