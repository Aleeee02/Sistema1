CREATE TABLE IF NOT EXISTS public.alertas_suscripciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
    tipo VARCHAR(30) NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    destinatario VARCHAR(255) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    error TEXT,
    enviado_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_alerta_suscripcion_evento UNIQUE (empresa_id, tipo, fecha_vencimiento),
    CONSTRAINT ck_alerta_suscripcion_tipo CHECK (tipo IN ('vence_7_dias','vence_3_dias','vence_hoy','periodo_gracia','acceso_bloqueado')),
    CONSTRAINT ck_alerta_suscripcion_estado CHECK (estado IN ('pendiente','enviada','error'))
);

CREATE INDEX IF NOT EXISTS idx_alertas_suscripciones_empresa_fecha
    ON public.alertas_suscripciones (empresa_id, created_at DESC);

ALTER TABLE public.alertas_suscripciones ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.alertas_suscripciones FROM anon, authenticated;
