# Bitácora IA

## 2026-09-18 — Preparación inicial

- Inspección de carpeta vacía y documento proporcionado.
- Incorporación íntegra de AGENTS.md.
- Creación de backend, frontend, documentación y dependencias del stack autorizado.
- Plantilla de variables vacías para secretos y archivo local ignorado.
- Sin implementación de políticas académicas ni acceso a información real.
- Git y Node disponibles; Python no encontrado en PATH.
- No se ejecutaron pruebas de aplicación: aún no existe código ejecutable.

## 2026-09-18 — Saludo integrado en localhost

- Solicitud del usuario: instalar y ejecutar DRF + React mostrando Hola mundo.
- Python 3.12.10 encontrado en el perfil del usuario; entorno .venv instalado.
- React/React DOM y Vite instalados, versiones fijadas en archivos de bloqueo.
- Vite justificado como herramienta de desarrollo, compilación y proxy de React.
- Endpoint DRF público sin datos sensibles y frontend con carga/error/reintento.
- Clave Django generada únicamente en .env local, sin imprimirla.
- Sin persistencia requerida para el saludo; PostgreSQL pendiente, sin SQLite.
- Verificaciones: pip check, Django check, build, HTTP directo/proxy y navegador.
- No se implementaron ni alteraron reglas académicas; AGENTS.md intacto.

## 2026-09-18 — Autenticación y administración institucional

- Confirmación del usuario: volcan administra globalmente; signup es privado.
- Confirmación del usuario: programas por universidad y programa obligatorio para estudiantes.
- PostgreSQL 17.11 local instalado desde EDB, datos y credenciales excluidos de Git.
- User personalizado y perfiles Administrator, Teacher y Student; IDs como códigos.
- Migración inicial aplicada; no se eliminó ni sustituyó información existente.
- Cuenta inicial creada con hash de contraseña; secreto ausente del código y documentación.
- Sesiones Django con cookie HttpOnly, CSRF también en login y limitación de intentos.
- Generación de correo institucional validada en backend; duplicados rechazados.
- Bienvenida, login, navbar, universidades, programas y alta de docentes/estudiantes.
- 22 pruebas Django sobre PostgreSQL aprobadas. check, revisión de migraciones,
  pip check y compilación Vite aprobados.
- Verificado en navegador: login de volcan, afiliación, programa, alta de estudiante
  y correo generado. Datos ficticios retirados sin eliminar datos del usuario.
- Corrección detectada en pruebas: normalizar correos vacíos de administradores a NULL.
- AGENTS.md conservado; ASSUMPTIONS.md y ADR documentan las decisiones aprobadas.
