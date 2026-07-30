const colors: Record<string, string> = {
  borrador: "bg-slate-100 text-slate-600 ring-slate-500/10",
  recepcion: "bg-cyan-50 text-cyan-700 ring-cyan-600/10",
  diagnostico: "bg-violet-50 text-violet-700 ring-violet-600/10",
  en_proceso: "bg-blue-50 text-blue-700 ring-blue-600/10",
  esperando_aprobacion: "bg-amber-50 text-amber-700 ring-amber-600/15",
  aprobada: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
  terminada: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
  entregada: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
  cancelada: "bg-red-50 text-red-700 ring-red-600/10",
  enviada: "bg-blue-50 text-blue-700 ring-blue-600/10",
  rechazada: "bg-red-50 text-red-700 ring-red-600/10",
  vencida: "bg-amber-50 text-amber-700 ring-amber-600/15",
  solicitada: "bg-cyan-50 text-cyan-700 ring-cyan-600/10",
  en_transito: "bg-violet-50 text-violet-700 ring-violet-600/10",
  recibida: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
};

export function StatusBadge({ status, label }: { status: string; label: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-bold ring-1 ring-inset ${
        colors[status] ?? colors.en_proceso
      }`}
    >
      {label}
    </span>
  );
}
