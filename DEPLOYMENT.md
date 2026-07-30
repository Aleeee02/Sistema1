# Despliegue

La aplicación incluye contenedores separados para FastAPI y Next.js. PostgreSQL
y los archivos continúan alojados en Supabase.

## Variables necesarias

Antes de desplegar, completa `backend/.env`:

- `APP_ENV=production`
- `DATABASE_URL`
- `JWT_SECRET`
- `CORS_ORIGINS` con el dominio público
- `FRONTEND_URL` con el dominio público
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- variables `SMTP_*`

`FASTAPI_URL` es una variable privada del servidor Next.js. Dentro de Docker se
configura automáticamente como `http://backend:8000/api/v1`.

## Inicio con Docker

```powershell
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d
```

Antes de publicar una versión nueva:

1. Crea un respaldo.
2. Revisa `python -m scripts.migrate --status`.
3. Aplica `python -m scripts.migrate` si existen cambios pendientes.
4. Construye y publica los dos servicios.

No expongas directamente el puerto 8000 del backend a Internet sin un proxy
HTTPS. En producción el frontend y FastAPI deben utilizar HTTPS.
