ALTER TABLE public.empresas
    ADD COLUMN IF NOT EXISTS dias_gracia INTEGER NOT NULL DEFAULT 5;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_empresas_dias_gracia') THEN
        ALTER TABLE public.empresas ADD CONSTRAINT ck_empresas_dias_gracia
            CHECK (dias_gracia BETWEEN 0 AND 60);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.pagos_suscripciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES public.empresas(id) ON DELETE RESTRICT,
    plan_codigo VARCHAR(30) NOT NULL,
    monto NUMERIC(12,2) NOT NULL,
    moneda VARCHAR(3) NOT NULL DEFAULT 'PEN',
    ciclo VARCHAR(20) NOT NULL,
    metodo_pago VARCHAR(30) NOT NULL,
    referencia VARCHAR(120),
    periodo_inicio DATE NOT NULL,
    periodo_fin DATE NOT NULL,
    pagado_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registrado_por UUID NOT NULL REFERENCES public.usuarios(id) ON DELETE RESTRICT,
    observaciones TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_pago_suscripcion_monto CHECK (monto >= 0),
    CONSTRAINT ck_pago_suscripcion_ciclo CHECK (ciclo IN ('mensual','trimestral','semestral','anual')),
    CONSTRAINT ck_pago_suscripcion_metodo CHECK (metodo_pago IN ('yape','plin','transferencia','efectivo','tarjeta','otro')),
    CONSTRAINT ck_pago_suscripcion_periodo CHECK (periodo_fin >= periodo_inicio)
);

CREATE INDEX IF NOT EXISTS idx_pagos_suscripciones_empresa_fecha
    ON public.pagos_suscripciones (empresa_id, pagado_at DESC);

ALTER TABLE public.pagos_suscripciones ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.pagos_suscripciones FROM anon, authenticated;
