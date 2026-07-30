import type { LucideIcon } from "lucide-react";

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
}) {
  return (
    <article className="group rounded-2xl border border-white/80 bg-white/90 p-5 shadow-[0_8px_30px_rgba(15,23,42,0.05)] backdrop-blur transition duration-200 hover:-translate-y-1 hover:shadow-[0_16px_40px_rgba(15,23,42,0.09)]">
      <div className="flex items-start justify-between">
        <div className="text-[11px] font-medium text-slate-400">{label}</div>
        <div className="grid size-9 place-items-center rounded-xl bg-blue-50 text-blue-600 transition group-hover:bg-blue-600 group-hover:text-white">
          <Icon size={16} />
        </div>
      </div>
      <div className="-mt-2 text-2xl font-bold tracking-tight text-slate-900">{value}</div>
      <div className="mt-2 text-[11px] font-medium text-emerald-600">{detail}</div>
    </article>
  );
}
