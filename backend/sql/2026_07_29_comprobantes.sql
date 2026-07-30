CREATE TABLE IF NOT EXISTS public.comprobantes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES public.empresas(id),
    sucursal_id UUID NOT NULL REFERENCES public.sucursales(id),
    orden_id UUID NOT NULL REFERENCES public.ordenes_trabajo(id),
    cliente_id UUID NOT NULL REFERENCES public.clientes(id),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('boleta','factura','nota_venta')),
    serie VARCHAR(10) NOT NULL,
    numero BIGINT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'emitido' CHECK (estado IN ('emitido','anulado')),
    cliente_nombre VARCHAR(200) NOT NULL,
    cliente_documento VARCHAR(20) NOT NULL,
    cliente_direccion TEXT,
    moneda VARCHAR(3) NOT NULL DEFAULT 'PEN',
    subtotal NUMERIC(12,2) NOT NULL,
    descuento NUMERIC(12,2) NOT NULL,
    impuesto NUMERIC(12,2) NOT NULL,
    total NUMERIC(12,2) NOT NULL,
    observaciones TEXT,
    emitido_por UUID NOT NULL REFERENCES public.usuarios(id),
    emitido_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    anulado_at TIMESTAMPTZ,
    motivo_anulacion TEXT,
    UNIQUE (empresa_id, serie, numero)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_comprobante_emitido_orden ON public.comprobantes(orden_id) WHERE estado='emitido';
CREATE INDEX IF NOT EXISTS idx_comprobantes_empresa_fecha ON public.comprobantes(empresa_id, emitido_at DESC);

CREATE TABLE IF NOT EXISTS public.comprobantes_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES public.empresas(id),
    comprobante_id UUID NOT NULL REFERENCES public.comprobantes(id) ON DELETE CASCADE,
    descripcion VARCHAR(250) NOT NULL,
    cantidad NUMERIC(10,2) NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12,2) NOT NULL CHECK (precio_unitario >= 0),
    descuento NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (descuento >= 0),
    total NUMERIC(12,2) NOT NULL CHECK (total >= 0)
);
ALTER TABLE public.comprobantes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comprobantes_items ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.comprobantes, public.comprobantes_items FROM anon, authenticated;
