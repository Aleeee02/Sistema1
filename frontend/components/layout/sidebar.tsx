"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOut } from "lucide-react";
import { navSections } from "@/lib/navigation";

export function Sidebar() {
  const pathname = usePathname();
  const [session, setSession] = useState<{
    nombres: string;
    apellidos: string;
    permisos: string[];
    empresa: { nombre: string; rol: string; color_primario: string };
  } | null>(null);

  useEffect(() => {
    fetch("/api/auth/me", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : null)
      .then(setSession)
      .catch(() => setSession(null));
  }, []);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  return (
    <aside className="border-b border-slate-200/80 bg-white/90 backdrop-blur-xl lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col lg:border-b-0 lg:border-r">
      <div className="flex min-h-[76px] items-center gap-3 border-b border-slate-100 px-4">
        <div className="grid size-12 place-items-center rounded-2xl text-sm font-black tracking-wide text-white shadow-lg shadow-blue-900/15" style={{ backgroundColor: session?.empresa.color_primario || "#1d4ed8" }}>
          {session?.empresa.nombre?.slice(0, 3).toUpperCase() || "NAP"}
        </div>
        <div>
          <div className="text-[13px] font-bold leading-tight text-slate-900">
            {session?.empresa.nombre || "Rectificaciones y Servicios"}
          </div>
          <div className="mt-0.5 text-[10px] font-medium text-slate-400">
            Especialistas en motor
          </div>
        </div>
      </div>

      <nav
        className="flex gap-2 overflow-x-auto p-2 lg:flex-1 lg:flex-col lg:overflow-y-auto lg:p-3"
        aria-label="Navegación principal"
      >
        {navSections.map((section) => {
          const items = section.items.filter((item) =>
            session ? session.permisos.includes(item.permission) : item.href === "/dashboard",
          );
          if (items.length === 0) return null;
          return (
          <div className="flex shrink-0 lg:mb-4 lg:block" key={section.label}>
            <div className="hidden px-3 pb-2 pt-1 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400 lg:block">
              {section.label}
            </div>
            {items.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  className={`group relative mb-1 flex min-h-10 items-center gap-2.5 whitespace-nowrap rounded-xl px-3 text-[13px] font-medium transition ${
                    active
                      ? "bg-blue-50 text-blue-700 shadow-[inset_0_0_0_1px_rgba(37,99,235,0.08)]"
                      : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                  href={item.href}
                  key={item.href}
                >
                  {active ? (
                    <span className="absolute inset-y-2 left-0 w-0.5 rounded-r bg-blue-600" />
                  ) : null}
                  <Icon
                    size={17}
                    className={active ? "text-blue-600" : "text-slate-400 group-hover:text-slate-600"}
                  />
                  {item.label}
                  {"badge" in item && item.badge ? (
                    <span className="ml-auto rounded-full bg-red-500 px-1.5 py-0.5 text-[9px] font-bold text-white shadow-sm">
                      {item.badge}
                    </span>
                  ) : null}
                </Link>
              );
            })}
          </div>
          );
        })}
      </nav>

      <div className="hidden border-t border-slate-100 p-3 lg:block">
        <div className="flex items-center gap-3 rounded-2xl bg-slate-50 p-3">
          <div className="grid size-9 place-items-center rounded-xl bg-slate-800 text-[11px] font-bold text-white">
            {session ? `${session.nombres[0] ?? ""}${session.apellidos[0] ?? ""}`.toUpperCase() : "US"}
          </div>
          <div className="min-w-0">
            <div className="truncate text-xs font-bold text-slate-800">
              {session ? `${session.nombres} ${session.apellidos}` : "Usuario"}
            </div>
            <div className="truncate text-[10px] capitalize text-slate-400">
              {session?.empresa.rol ?? "Cargando acceso"}
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            className="ml-auto grid size-8 place-items-center rounded-lg text-slate-400 transition hover:bg-white hover:text-red-600"
            aria-label="Cerrar sesión"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}
