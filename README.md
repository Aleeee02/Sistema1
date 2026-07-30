# Taller SaaS

Proyecto separado en:

- `backend/`: API REST con FastAPI, SQLAlchemy asíncrono y PostgreSQL de Supabase.
- `frontend/`: interfaz con Next.js, React y TypeScript.

## Backend

1. Completa `backend/.env`, especialmente `DATABASE_URL` y `JWT_SECRET`.
2. Crea el entorno e instala las dependencias:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La documentación interactiva estará en `http://localhost:8000/docs`.
El endpoint `GET /api/v1/health/database` comprueba la conexión real con PostgreSQL.

Para comprobar la conexión desde la terminal también puedes ejecutar:

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.check_db_connection
```

### Primer acceso

Si la base todavía no tiene empresas ni usuarios, ejecuta una sola vez:

```powershell
cd backend
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe .\scripts\bootstrap.py
```

El asistente crea la primera empresa, su sucursal principal y un administrador.
Después podrás iniciar sesión en `http://localhost:3000/login`.

## Frontend

1. Coloca temporalmente un `empresa_id` válido en `frontend/.env.local`.
2. Instala y ejecuta:

```bash
cd frontend
npm install
npm run dev
```

La aplicación estará en `http://localhost:3000`.

## Seguridad

Nunca subas `.env`, `.env.local`, la contraseña de PostgreSQL, `service_role` ni `JWT_SECRET`.
Next.js solo se comunica con FastAPI; no recibe credenciales de PostgreSQL.

## Recuperación de contraseña

En desarrollo, el sistema puede mostrar un enlace de recuperación directamente.
En producción configura `FRONTEND_URL` y las variables `SMTP_*` de
`backend/.env`. El enlace se enviará al correo del usuario y vencerá después de
30 minutos. Usa una contraseña de aplicación del proveedor de correo; nunca
coloques la contraseña personal de la cuenta.
