ALTER TABLE public.usuarios
    ADD COLUMN IF NOT EXISTS es_superadmin BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.empresas
    ADD COLUMN IF NOT EXISTS plan_codigo VARCHAR(30) NOT NULL DEFAULT 'basico',
    ADD COLUMN IF NOT EXISTS suscripcion_estado VARCHAR(20) NOT NULL DEFAULT 'prueba',
    ADD COLUMN IF NOT EXISTS suscripcion_inicio DATE NOT NULL DEFAULT CURRENT_DATE,
    ADD COLUMN IF NOT EXISTS suscripcion_fin DATE,
    ADD COLUMN IF NOT EXISTS max_usuarios INTEGER NOT NULL DEFAULT 5,
    ADD COLUMN IF NOT EXISTS max_sucursales INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS notas_internas TEXT;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_empresas_plan') THEN
        ALTER TABLE public.empresas ADD CONSTRAINT ck_empresas_plan
            CHECK (plan_codigo IN ('basico', 'profesional', 'empresarial'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_empresas_suscripcion_estado') THEN
        ALTER TABLE public.empresas ADD CONSTRAINT ck_empresas_suscripcion_estado
            CHECK (suscripcion_estado IN ('prueba', 'activa', 'vencida', 'cancelada'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_empresas_limites') THEN
        ALTER TABLE public.empresas ADD CONSTRAINT ck_empresas_limites
            CHECK (max_usuarios > 0 AND max_sucursales > 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_empresas_suscripcion_fechas') THEN
        ALTER TABLE public.empresas ADD CONSTRAINT ck_empresas_suscripcion_fechas
            CHECK (suscripcion_fin IS NULL OR suscripcion_fin >= suscripcion_inicio);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_empresas_suscripcion
    ON public.empresas (suscripcion_estado, suscripcion_fin);
CREATE INDEX IF NOT EXISTS idx_usuarios_superadmin
    ON public.usuarios (es_superadmin) WHERE es_superadmin = TRUE;
