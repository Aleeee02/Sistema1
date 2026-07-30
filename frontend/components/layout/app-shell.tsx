"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { NotificationBell } from "@/components/layout/notification-bell";
import { routeTitles } from "@/lib/navigation";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const title = routeTitles[pathname] ?? "Gestión del taller";

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[256px_minmax(0,1fr)]">
      <Sidebar />
      <main className="min-w-0">
        <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between border-b border-slate-200/80 bg-white/80 px-4 shadow-[0_1px_0_rgba(15,23,42,0.02)] backdrop-blur-xl sm:px-7">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
              Panel de gestión
            </div>
            <div className="text-[15px] font-bold text-slate-900">{title}</div>
          </div>
          <div className="flex items-center gap-2">
            <NotificationBell />
          </div>
        </header>
        <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-7 sm:py-8">{children}</div>
      </main>
    </div>
  );
}
