"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  Gauge,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Wrench,
} from "lucide-react";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = new FormData(event.currentTarget);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "No fue posible iniciar sesión");
      }
      router.replace(searchParams.get("next") || "/dashboard");
      router.refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "No fue posible iniciar sesión",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative grid min-h-screen overflow-hidden bg-slate-950 lg:grid-cols-[1.08fr_0.92fr]">
      <div className="pointer-events-none absolute -left-32 top-20 size-96 rounded-full bg-blue-600/20 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 left-1/3 size-80 rounded-full bg-orange-500/10 blur-3xl" />

      <section className="relative hidden flex-col justify-between p-12 lg:flex xl:p-16">
        <div className="flex items-center gap-3">
          <div className="grid size-12 place-items-center rounded-2xl bg-gradient-to-br from-blue-500 to-orange-500 text-sm font-black text-white shadow-xl shadow-blue-950/50">
            NAP
          </div>
          <div>
            <div className="text-sm font-bold text-white">Gestión de taller</div>
            <div className="text-xs text-slate-400">Operaciones en un solo lugar</div>
          </div>
        </div>

        <div className="max-w-xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-400/10 px-3 py-1.5 text-xs font-semibold text-blue-300">
            <Wrench size={14} />
            Software especializado para talleres
          </div>
          <h1 className="text-5xl font-bold leading-[1.08] tracking-tight text-white xl:text-6xl">
            Controla cada trabajo,
            <span className="block bg-gradient-to-r from-blue-400 to-orange-400 bg-clip-text text-transparent">
              desde la recepción.
            </span>
          </h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-slate-400">
            Órdenes, agenda, cotizaciones, inventario y pagos conectados con la
            operación real de tu empresa.
          </p>
          <div className="mt-10 grid max-w-lg grid-cols-2 gap-4">
            {[
              [Gauge, "Indicadores en tiempo real"],
              [ShieldCheck, "Datos separados por empresa"],
              [CheckCircle2, "Seguimiento de cada orden"],
              [LockKeyhole, "Acceso seguro por roles"],
            ].map(([Icon, text]) => (
              <div
                className="flex items-center gap-2 text-sm text-slate-300"
                key={String(text)}
              >
                <Icon size={16} className="text-blue-400" />
                {String(text)}
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs text-slate-600">
          Sistema privado para empresas autorizadas.
        </p>
      </section>

      <section className="relative flex min-h-screen items-center justify-center bg-white px-5 py-10 lg:rounded-l-[2.5rem]">
        <div className="w-full max-w-md">
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <div className="grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-blue-600 to-orange-500 text-xs font-black text-white">
              NAP
            </div>
            <div className="font-bold text-slate-900">Gestión de taller</div>
          </div>

          <div className="mb-8">
            <div className="text-xs font-bold uppercase tracking-[0.16em] text-blue-600">
              Bienvenido
            </div>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
              Inicia sesión
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              Utiliza las credenciales asignadas por tu empresa.
            </p>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-slate-700">
                Correo electrónico
              </span>
              <span className="relative block">
                <Mail
                  size={18}
                  className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <input
                  className="h-12 w-full rounded-xl border border-slate-200 bg-slate-50 pl-11 pr-4 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10"
                  type="email"
                  name="email"
                  autoComplete="email"
                  placeholder="administrador@empresa.com"
                  required
                />
              </span>
              <Link href="/recuperar-password" className="mt-2 block text-right text-xs font-semibold text-blue-600">¿Olvidaste tu contraseña?</Link>
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-slate-700">
                Contraseña
              </span>
              <span className="relative block">
                <LockKeyhole
                  size={18}
                  className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <input
                  className="h-12 w-full rounded-xl border border-slate-200 bg-slate-50 pl-11 pr-12 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10"
                  type={showPassword ? "text" : "password"}
                  name="password"
                  autoComplete="current-password"
                  placeholder="Mínimo 8 caracteres"
                  minLength={8}
                  required
                />
                <button
                  className="absolute right-3 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </span>
            </label>

            {error ? (
              <div
                className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                role="alert"
              >
                {error}
              </div>
            ) : null}

            <button
              className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-blue-600 text-sm font-bold text-white shadow-lg shadow-blue-600/20 transition hover:-translate-y-0.5 hover:bg-blue-700 disabled:cursor-wait disabled:opacity-60"
              type="submit"
              disabled={loading}
            >
              {loading ? "Verificando…" : "Ingresar al sistema"}
              {!loading ? <ArrowRight size={17} /> : null}
            </button>
          </form>

          <p className="mt-8 text-center text-xs leading-5 text-slate-400">
            Si no tienes acceso, comunícate con el administrador de tu empresa.
          </p>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center bg-slate-950">
          <div className="size-8 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
