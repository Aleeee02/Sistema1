CREATE TABLE IF NOT EXISTS public.metodos_pago_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES public.empresas(id) ON UPDATE CASCADE ON DELETE CASCADE,
    metodo VARCHAR(30) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    nombre_mostrar VARCHAR(80) NOT NULL,
    configuracion JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_metodos_pago_empresa_metodo UNIQUE (empresa_id, metodo),
    CONSTRAINT ck_metodos_pago_metodo CHECK (metodo IN ('efectivo','tarjeta','transferencia','yape','plin','otro'))
);

CREATE INDEX IF NOT EXISTS idx_metodos_pago_empresa_activo
ON public.metodos_pago_config (empresa_id, activo);

DROP TRIGGER IF EXISTS trg_metodos_pago_updated_at ON public.metodos_pago_config;
CREATE TRIGGER trg_metodos_pago_updated_at
BEFORE UPDATE ON public.metodos_pago_config
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.metodos_pago_config ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.metodos_pago_config FROM anon, authenticated;
