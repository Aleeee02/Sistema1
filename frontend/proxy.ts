import { NextRequest, NextResponse } from "next/server";

const protectedRoutes = [
  "/dashboard",
  "/plataforma",
  "/perfil",
  "/agenda",
  "/pagos",
  "/inspecciones",
  "/usuarios",
  "/roles",
  "/configuracion",
  "/comprobantes",
  "/auditoria",
  "/ordenes",
  "/cotizaciones",
  "/inventario",
  "/empleados",
  "/clientes",
  "/estadisticas",
  "/reportes",
];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get("access_token")?.value);
  const isProtected = protectedRoutes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );

  if (isProtected && !hasSession) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (pathname === "/login" && hasSession) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/plataforma/:path*",
    "/perfil/:path*",
    "/agenda/:path*",
    "/pagos/:path*",
    "/inspecciones/:path*",
    "/usuarios/:path*",
    "/roles/:path*",
    "/configuracion/:path*",
    "/comprobantes/:path*",
    "/auditoria/:path*",
    "/ordenes/:path*",
    "/cotizaciones/:path*",
    "/inventario/:path*",
    "/empleados/:path*",
    "/clientes/:path*",
    "/estadisticas/:path*",
    "/reportes/:path*",
    "/login",
  ],
};
