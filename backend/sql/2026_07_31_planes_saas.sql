CREATE TABLE IF NOT EXISTS public.planes_saas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo VARCHAR(30) NOT NULL UNIQUE,
    nombre VARCHAR(80) NOT NULL,
    descripcion TEXT,
    precio_mensual NUMERIC(12,2) NOT NULL DEFAULT 0,
    max_usuarios INTEGER NOT NULL DEFAULT 5,
    max_sucursales INTEGER NOT NULL DEFAULT 1,
    modulos JSONB NOT NULL DEFAULT '[]'::jsonb,
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_planes_precio_limites CHECK (
        precio_mensual >= 0 AND max_usuarios > 0 AND max_sucursales > 0
    ),
    CONSTRAINT ck_planes_estado CHECK (estado IN ('activo', 'inactivo'))
);

INSERT INTO public.planes_saas
    (codigo, nombre, descripcion, precio_mensual, max_usuarios, max_sucursales, modulos)
VALUES
    ('basico', 'Básico', 'Operación esencial para un taller pequeño.', 0, 5, 1,
     '["dashboard","agenda","clientes","vehiculos","ordenes","cotizaciones","inspecciones","pagos","servicios","inventario","empleados","configuracion","comprobantes"]'::jsonb),
    ('profesional', 'Profesional', 'Gestión completa para talleres en crecimiento.', 0, 15, 3,
     '["dashboard","agenda","clientes","vehiculos","ordenes","cotizaciones","inspecciones","pagos","servicios","inventario","transferencias","empleados","sucursales","usuarios","estadisticas","reportes","configuracion","comprobantes"]'::jsonb),
    ('empresarial', 'Empresarial', 'Todas las funciones para organizaciones con varias sedes.', 0, 100, 20,
     '["dashboard","agenda","clientes","vehiculos","ordenes","cotizaciones","inspecciones","pagos","servicios","inventario","transferencias","empleados","sucursales","usuarios","estadisticas","reportes","configuracion","comprobantes","auditoria"]'::jsonb)
ON CONFLICT (codigo) DO NOTHING;

-- La empresa desde la cual se administra la plataforma conserva acceso completo.
UPDATE public.empresas AS empresa
SET plan_codigo = 'empresarial',
    max_usuarios = GREATEST(empresa.max_usuarios, 100),
    max_sucursales = GREATEST(empresa.max_sucursales, 20)
WHERE EXISTS (
    SELECT 1
    FROM public.usuarios_empresas AS membresia
    JOIN public.usuarios AS usuario ON usuario.id = membresia.usuario_id
    WHERE membresia.empresa_id = empresa.id
      AND usuario.es_superadmin = TRUE
);

CREATE TRIGGER trg_planes_saas_updated_at
BEFORE UPDATE ON public.planes_saas
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.planes_saas ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.planes_saas FROM anon, authenticated;
