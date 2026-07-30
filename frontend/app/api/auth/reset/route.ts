import { NextRequest, NextResponse } from "next/server";
const API_URL=process.env.FASTAPI_URL??"http://localhost:8000/api/v1";
export async function POST(request:NextRequest){const response=await fetch(`${API_URL}/auth/restablecer-password`,{method:"POST",headers:{"Content-Type":"application/json"},body:await request.text(),cache:"no-store"});return new NextResponse(null,{status:response.status})}
