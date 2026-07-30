# Operaciones de base de datos

## Migraciones

Los archivos de `backend/sql` se ejecutan en orden y quedan registrados con una
firma para impedir repeticiones o modificaciones accidentales:

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.migrate --status
.\.venv\Scripts\python.exe -m scripts.migrate
```

Antes de aplicar migraciones en producción crea un respaldo.

Si la base ya recibió manualmente todos los archivos SQL antes de instalar este
control, adopta una sola vez el estado existente sin volver a ejecutar el SQL:

```powershell
.\.venv\Scripts\python.exe -m scripts.migrate --baseline
```

## Respaldos

Instala las herramientas cliente de PostgreSQL para disponer de `pg_dump` y
`pg_restore`. Después ejecuta:

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.backup_database
```

Los archivos se guardan en `backend/backups`, se verifican automáticamente y
los que superen 30 días se eliminan. Puedes cambiar la retención:

```powershell
.\.venv\Scripts\python.exe -m scripts.backup_database --retention-days 60
```

Nunca sincronices la carpeta de respaldos con un repositorio público.
