import type { LucideIcon } from "lucide-react";
import { PageHeading } from "@/components/ui/page-heading";

export function ModulePlaceholder({
  title,
  description,
  icon: Icon,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
}) {
  return (
    <>
      <PageHeading title={title} subtitle={description} />
      <section className="grid min-h-[360px] place-items-center rounded-3xl border border-dashed border-blue-200 bg-gradient-to-br from-white via-white to-blue-50/60 p-8 text-center shadow-sm">
        <div className="max-w-md">
          <div className="mx-auto mb-5 grid size-16 place-items-center rounded-2xl bg-blue-600 text-white shadow-xl shadow-blue-600/20">
            <Icon size={30} />
          </div>
          <h2 className="text-lg font-bold text-slate-900">Módulo preparado</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">
          La ruta ya está separada del HTML original. En la siguiente etapa se
          conectarán sus formularios y operaciones con FastAPI.
          </p>
        </div>
      </section>
    </>
  );
}
