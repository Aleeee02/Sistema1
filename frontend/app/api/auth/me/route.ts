import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_URL = process.env.FASTAPI_URL ?? "http://localhost:8000/api/v1";

export async function GET() {
  const token = (await cookies()).get("access_token")?.value;
  if (!token) {
    return NextResponse.json({ detail: "No existe una sesión" }, { status: 401 });
  }

  const response = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  const body = await response.json().catch(() => ({
    detail: "No fue posible consultar la sesión",
  }));
  return NextResponse.json(body, { status: response.status });
}
