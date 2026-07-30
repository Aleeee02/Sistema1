export interface Cliente {
  id: string;
  empresa_id: string;
  tipo_persona: "natural" | "juridica";
  tipo_documento: string;
  numero_documento: string;
  nombres: string | null;
  apellidos: string | null;
  razon_social: string | null;
  telefono: string | null;
  email: string | null;
  direccion: string | null;
  autoriza_contacto: boolean;
  observaciones: string | null;
  estado: string;
  created_at: string;
  updated_at: string;
}

export interface Vehiculo {
  id: string;
  empresa_id: string;
  placa: string;
  vin: string | null;
  marca: string | null;
  modelo: string | null;
  anio: number | null;
  color: string | null;
  combustible: string | null;
  motor: string | null;
  cilindrada: string | null;
  estado: string;
  created_at: string;
  updated_at: string;
}

export interface OrdenTrabajo {
  id: string;
  empresa_id: string;
  sucursal_id: string;
  numero: number;
  estado: string;
  cliente_id: string;
  vehiculo_id: string;
  falla_reportada: string | null;
  diagnostico: string | null;
  observaciones: string | null;
  kilometraje: number | null;
  nivel_combustible: number | null;
  total: string;
  saldo: string;
  fecha_recepcion: string;
  fecha_estimada_entrega: string | null;
  fecha_entrega: string | null;
  cliente_nombre: string;
  cliente_documento: string;
  vehiculo_placa: string;
  vehiculo_descripcion: string;
  sucursal_nombre: string;
}
