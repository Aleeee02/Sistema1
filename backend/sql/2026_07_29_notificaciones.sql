CREATE TABLE IF NOT EXISTS public.notificaciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
    sucursal_id UUID REFERENCES public.sucursales(id) ON DELETE CASCADE,
    usuario_id UUID REFERENCES public.usuarios(id) ON DELETE CASCADE,
    tipo VARCHAR(40) NOT NULL,
    titulo VARCHAR(150) NOT NULL,
    mensaje TEXT NOT NULL,
    enlace VARCHAR(255),
    leida BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    leida_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_notificaciones_empresa_fecha ON public.notificaciones(empresa_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario_no_leida ON public.notificaciones(usuario_id, leida) WHERE leida = FALSE;
ALTER TABLE public.notificaciones ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.notificaciones FROM anon, authenticated;
