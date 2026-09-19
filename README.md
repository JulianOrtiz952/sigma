# SIGMA

Sistema Integral de Gestión de Matrículas Académicas.

## Funcionalidades disponibles

- Bienvenida y login con sesión Django.
- Cuenta inicial `volcan`, administradora global, creada localmente con la
  contraseña suministrada por el propietario (no almacenada en el repositorio).
- Navbar privada: Creación de usuarios y Universidades.
- Afiliación de universidades con dominio institucional y creación de programas.
- Registro privado de docentes y estudiantes. Programa obligatorio para estudiantes.
- Correo generado por el backend: `Andres Julian Ortiz Jaimes` + `ufps.edu.co`
  produce `andresjulianoj@ufps.edu.co`.
- Código = ID incremental del perfil; contraseña inicial = código, salvo que el
  administrador indique una personalizada. Se almacenan hashes, no texto plano.
- Docentes y estudiantes ingresan con su correo y ven solo su propio perfil.

## Instalación

Probado con Python 3.12.10, Node 24.19.0 y PostgreSQL 17.11 en Windows.
Desde la raíz en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm.cmd --prefix frontend ci
```

Copiar `.env.example` a `.env` únicamente si no existe. Configurar la clave secreta
Django y credenciales PostgreSQL localmente, sin publicarlas. El formato admitido
es `KEY=value` sin comillas ni expansión; el entorno del proceso tiene precedencia.

En este equipo PostgreSQL está instalado en `.local/postgresql/pgsql/`, y el
clúster en `.local/postgres-data/`. Para preparar o arrancar ese clúster:

```powershell
.\.venv\Scripts\python.exe scripts/setup_database.py
.\.venv\Scripts\python.exe backend/manage.py migrate
```

El script requiere los binarios oficiales previamente extraídos en esa ruta.
Fuente: https://www.enterprisedb.com/download-postgresql-binaries (17.11, Windows x64).
En otro equipo se puede usar una instalación PostgreSQL existente y configurar el
`.env` directamente, sin ejecutar el script de clúster local. El usuario de BD
necesita poder crear una base separada para ejecutar la suite de pruebas.

Para crear la cuenta inicial en una base nueva (pide la contraseña sin mostrarla):

```powershell
.\.venv\Scripts\python.exe backend/manage.py create_initial_admin --username volcan
```

Si la cuenta ya existe, el comando se detiene sin modificarla. No repetirlo para
cambiar contraseñas. La variable temporal SIGMA_ADMIN_PASSWORD permite ejecución
no interactiva; no se debe añadir al repositorio ni al frontend.

## Ejecución local

Abrir dos terminales desde la raíz, con PostgreSQL activo:

```powershell
# Terminal 1
.\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8000 --noreload
```

```powershell
# Terminal 2
npm.cmd --prefix frontend run dev
```

- Aplicación: http://localhost:5173
- Backend: http://127.0.0.1:8000/api/auth/session/
- Detener los procesos de cada terminal con Ctrl+C.
- Los servidores iniciados por el agente están en segundo plano y sus registros
  se guardan en `.local/`. El backend usa `--noreload`: reiniciarlo tras editar Python.

No ejecutar una segunda instancia si los puertos ya están ocupados. La aplicación
usa cookies del mismo origen; conviene mantener localhost durante toda la sesión.

Para detener el clúster local cuando no esté en uso:

```powershell
.\.local\postgresql\pgsql\bin\pg_ctl.exe -D .local/postgres-data stop -m fast
```

## Uso

1. Iniciar sesión con volcan y la contraseña que se indicó al crear la cuenta.
2. En Universidades, afiliar institución y dominio (sin @ ni https://).
3. Crear sus programas académicos en la misma sección.
4. En Creación de usuarios, elegir docente o estudiante, introducir nombres,
   ambos apellidos, universidad y programa cuando corresponda.
5. Guardar. El resultado muestra correo y código. Entregar las credenciales al
   titular por un canal privado. El sistema no envía correos ni crea buzones.

## API

| Ruta | Acceso y comportamiento |
| --- | --- |
| GET /api/auth/session/ | Estado de sesión y token CSRF |
| POST /api/auth/login/ | Login con username/password; exige CSRF |
| POST /api/auth/logout/ | Cierra sesión; exige autenticación y CSRF |
| GET/POST /api/auth/signup/ | Registro privado y lista, solo administradores |
| GET/POST /api/users/ | Mismo servicio administrativo de cuentas |
| GET/POST /api/universities/ | Consulta del alcance permitido; alta solo global |
| GET/POST /api/programs/ | Consulta/alta dentro del alcance institucional |
| GET /api/hello/ | Saludo público de compatibilidad, sin datos personales |

Los POST autenticados exigen X-CSRFToken. El frontend obtiene el token al consultar
la sesión y lo actualiza después del login. Las contraseñas nunca se devuelven.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe backend/manage.py check
.\.venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe backend/manage.py test accounts
npm.cmd --prefix frontend run build
```

Suite: 22 pruebas sobre correo, contraseñas, perfiles, duplicados, permisos,
aislamiento institucional, CSRF, sesiones y limitación de intentos de login.
Las pruebas usan una base PostgreSQL separada y la eliminan al terminar.

## Alcance y seguridad

`AGENTS.md` se mantiene íntegro. Consultar ASSUMPTIONS.md y docs/adr/ para decisiones.
Esta etapa no incluye matrículas, currículos, horarios, recuperación de contraseña
ni verificación de propiedad de correos. El código como contraseña inicial es la
política solicitada para esta etapa; debe revisarse antes de publicar en producción.

Las sesiones duran hasta ocho horas y usan cookies HttpOnly/SameSite=Lax.
En producción configurar HTTPS y COOKIE_SECURE=True, además de un servidor y
proxy de producción. La limitación de login usa caché local de Django y no es
un mecanismo distribuido contra ataques. Vite y runserver son solo de desarrollo.

.env, .local, dependencias, logs y respaldos están excluidos de Git. No incluir
secretos o datos reales en código, capturas o registros. Las variables del frontend
son públicas para el navegador; nunca poner credenciales allí.
