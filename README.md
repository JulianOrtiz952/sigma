# sigma

Sistema Integral de Gestión de Matrículas Académicas.

## Estructura

- `AGENTS.md`: reglas del proyecto, conservadas del documento original.
- `backend/`: espacio para Python, Django REST Framework y PostgreSQL.
- `frontend/`: espacio para React con JavaScript.
- `requirements.txt`: dependencias iniciales del backend.
- `.env.example`: plantilla pública sin secretos.
- `.env`: configuración local excluida de Git.
- `ASSUMPTIONS.md`: requisitos pendientes de definición.
- `BITACORA-IA.md`: registro de trabajo asistido.
- `docs/adr/`: decisiones arquitectónicas.

## Estado

Estructura inicial; aún no hay aplicación Django o React ni pruebas automatizadas.
Python no está disponible en el PATH de la terminal inspeccionada. Se verificaron
Git 2.55.0 y Node.js 24.19.0 mediante `git --version` y `node --version`.

## Preparación del backend (pendiente de ejecutar)

Instalar Python compatible con Django 5.2 y disponer de PostgreSQL local.
Desde la raíz, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

En otro clon, copiar `.env.example` a `.env` si no existe. Completar los secretos
localmente. Esta estructura todavía no carga el `.env` automáticamente.
No hay comandos de servidor, migraciones o pruebas disponibles aún.
Las versiones transitivas deberán fijarse tras resolver y validar el entorno.
Django 5.2 es la rama LTS: https://www.djangoproject.com/download/
Psycopg es el adaptador requerido para PostgreSQL; no se añaden otros frameworks.
El frontend queda preparado como carpeta, sin elegir herramientas adicionales.

## Información sensible

Nunca incluir credenciales, datos reales de estudiantes, archivos de producción o
respaldos en commits, documentación, capturas o registros. Usar datos sintéticos.
No colocar secretos en variables del frontend: el navegador puede leerlas.
`.gitignore` es una protección preventiva, no un detector de secretos.
Antes de cada commit revisar los archivos seleccionados y el diff.

```powershell
git check-ignore .env backend/.env frontend/.env.production
git diff --cached --name-only
git diff --cached --check
```
