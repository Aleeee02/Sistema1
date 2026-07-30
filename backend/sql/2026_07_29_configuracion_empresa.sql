ALTER TABLE public.empresas
    ADD COLUMN IF NOT EXISTS direccion_fiscal TEXT,
    ADD COLUMN IF NOT EXISTS telefono VARCHAR(30),
    ADD COLUMN IF NOT EXISTS email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS sitio_web VARCHAR(255),
    ADD COLUMN IF NOT EXISTS color_primario VARCHAR(7) NOT NULL DEFAULT '#2563EB',
    ADD COLUMN IF NOT EXISTS prefijo_orden VARCHAR(10) NOT NULL DEFAULT 'OT',
    ADD COLUMN IF NOT EXISTS prefijo_cotizacion VARCHAR(10) NOT NULL DEFAULT 'COT';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.empresas'::regclass
          AND conname = 'ck_empresas_color_primario'
    ) THEN
        ALTER TABLE public.empresas
        ADD CONSTRAINT ck_empresas_color_primario
        CHECK (color_primario ~ '^#[0-9A-Fa-f]{6}$');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.empresas'::regclass
          AND conname = 'ck_empresas_prefijos'
    ) THEN
        ALTER TABLE public.empresas
        ADD CONSTRAINT ck_empresas_prefijos
        CHECK (
            prefijo_orden ~ '^[A-Za-z0-9-]+$'
            AND prefijo_cotizacion ~ '^[A-Za-z0-9-]+$'
        );
    END IF;
END $$;
