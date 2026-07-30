import { NextResponse } from "next/server";
import { setAuthCookies } from "@/lib/auth-cookies";

const API_URL = process.env.FASTAPI_URL ?? "http://localhost:8000/api/v1";

export async function POST(request: Request) {
  const payload = await request.json();
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const body = await response.json().catch(() => ({
    detail: "No fue posible iniciar sesión",
  }));

  if (!response.ok) {
    return NextResponse.json(body, { status: response.status });
  }

  await setAuthCookies(body.access_token, body.refresh_token);
  return NextResponse.json({ usuario: body.usuario });
}
