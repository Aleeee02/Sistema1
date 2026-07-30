import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { clearAuthCookies, setAuthCookies } from "@/lib/auth-cookies";

const API_URL = process.env.FASTAPI_URL ?? "http://localhost:8000/api/v1";

export async function POST() {
  const store = await cookies();
  const refreshToken = store.get("refresh_token")?.value;
  if (!refreshToken) {
    return NextResponse.json({ detail: "No existe una sesión" }, { status: 401 });
  }

  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: "no-store",
  });
  const body = await response.json().catch(() => ({
    detail: "No fue posible renovar la sesión",
  }));
  if (!response.ok) {
    await clearAuthCookies();
    return NextResponse.json(body, { status: response.status });
  }

  await setAuthCookies(body.access_token, body.refresh_token);
  return NextResponse.json({ usuario: body.usuario });
}
