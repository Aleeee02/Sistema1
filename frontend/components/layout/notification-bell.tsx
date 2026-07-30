"use client";
import Link from "next/link";
import { Bell, CheckCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
type Notice={id:string;tipo:string;titulo:string;mensaje:string;enlace:string|null;leida:boolean;created_at:string};
export function NotificationBell(){
 const [items,setItems]=useState<Notice[]>([]),[open,setOpen]=useState(false);
 const load=useCallback(async()=>{try{setItems(await apiRequest<Notice[]>("/notificaciones"))}catch{}},[]);
 useEffect(()=>{const timer=setTimeout(()=>void load(),0);const interval=setInterval(()=>void load(),60000);return()=>{clearTimeout(timer);clearInterval(interval)}},[load]);
 const unread=items.filter(item=>!item.leida).length;
 async function read(item:Notice){if(!item.leida){await apiRequest(`/notificaciones/${item.id}/leer`,{method:"PATCH"});await load()}setOpen(false)}
 async function readAll(){await apiRequest("/notificaciones/leer-todas",{method:"POST"});await load()}
 return <div className="relative"><button onClick={()=>setOpen(!open)} className="relative grid size-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:text-blue-600" aria-label="Notificaciones"><Bell size={17}/>{unread?<span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-red-500 px-1 text-[10px] font-bold leading-5 text-white">{unread>9?"9+":unread}</span>:null}</button>
 {open?<div className="absolute right-0 top-12 z-50 w-[min(360px,calc(100vw-2rem))] overflow-hidden rounded-2xl border bg-white shadow-2xl"><div className="flex items-center justify-between border-b p-4"><div><strong>Notificaciones</strong><div className="text-xs text-slate-500">{unread} sin leer</div></div>{unread?<button onClick={()=>void readAll()} className="button"><CheckCheck size={14}/>Leer todas</button>:null}</div><div className="max-h-96 overflow-y-auto">{!items.length?<div className="p-10 text-center text-sm text-slate-500">No hay notificaciones.</div>:items.map(item=><Link href={item.enlace||"#"} onClick={()=>void read(item)} key={item.id} className={`block border-b p-4 transition hover:bg-slate-50 ${item.leida?"opacity-60":"bg-blue-50/40"}`}><div className="flex justify-between gap-3"><strong className="text-sm">{item.titulo}</strong>{!item.leida?<span className="mt-1 size-2 shrink-0 rounded-full bg-blue-600"/>:null}</div><p className="mt-1 text-xs text-slate-600">{item.mensaje}</p><div className="mt-2 text-[10px] text-slate-400">{new Date(item.created_at).toLocaleString("es-PE")}</div></Link>)}</div></div>:null}</div>
}
