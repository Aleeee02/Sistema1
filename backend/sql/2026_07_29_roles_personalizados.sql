-- Roles personalizados por empresa.
-- Ejecutar una sola vez en Supabase SQL Editor.

ALTER TABLE public.roles
    ADD COLUMN IF NOT EXISTS empresa_id UUID,
    ADD COLUMN IF NOT EXISTS es_sistema BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS estado VARCHAR(20) NOT NULL DEFAULT 'activo';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.roles'::regclass
          AND conname = 'fk_roles_empresa'
    ) THEN
        ALTER TABLE public.roles
        ADD CONSTRAINT fk_roles_empresa
        FOREIGN KEY (empresa_id) REFERENCES public.empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.roles'::regclass
          AND conname = 'ck_roles_estado'
    ) THEN
        ALTER TABLE public.roles
        ADD CONSTRAINT ck_roles_estado CHECK (estado IN ('activo', 'inactivo'));
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_empresa_nombre
ON public.roles (empresa_id, lower(nombre))
WHERE empresa_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.roles_permisos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL,
    rol_id UUID NOT NULL,
    permiso VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_roles_permisos_rol_permiso UNIQUE (rol_id, permiso),
    CONSTRAINT fk_roles_permisos_empresa
        FOREIGN KEY (empresa_id) REFERENCES public.empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_roles_permisos_rol
        FOREIGN KEY (rol_id) REFERENCES public.roles(id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_roles_permisos_empresa_rol
ON public.roles_permisos (empresa_id, rol_id);

ALTER TABLE public.roles_permisos ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.roles_permisos FROM anon, authenticated;
