# ADR 001 — Identidad, universidades y sesión local

Fecha: 2026-09-18. Alcance: autenticación y registro administrativo solicitado.

Se usa un User personalizado basado en AbstractUser desde la primera migración,
con perfiles OneToOne Administrator, Teacher y Student. El ID de cada perfil
estudiantil o docente sirve como código, respetando AGENTS.md. Student referencia
un programa obligatorio y deriva de él su universidad, evitando dos relaciones
institucionales contradictorias.

La cuenta inicial volcan tiene alcance global expresamente aprobado. El modelo
Administrator usa is_global=False por defecto y permite universidades asignadas;
las consultas y altas se filtran en backend. Ningún cliente puede crear una
cuenta administradora ni suministrar privilegios en signup.

Se usa PostgreSQL 17.11 local, descargado de EDB, proveedor enlazado por el sitio
oficial de PostgreSQL. Binarios, datos y credenciales están en .local (ignorado).
El servidor escucha solo en 127.0.0.1 con autenticación SCRAM-SHA-256. El rol sigma
no es superusuario; tiene CREATEDB para crear la base aislada de pruebas locales.
En producción deben separarse los roles y retirarse ese privilegio.

Django SessionAuthentication y el proxy Vite evitan nuevas dependencias de tokens
o CORS. Las sesiones usan cookies HttpOnly; CSRF se exige también para el login
anónimo. No se guardan tokens ni contraseñas en localStorage. La API entrega solo
los campos públicos necesarios para el usuario o administrador autorizado.

La contraseña inicial basada en el código fue solicitada explícitamente. Es
predecible, por lo que esta política requiere revisión antes de producción.
No se incorporó un cambio forzado de contraseña sin solicitarlo el usuario.
Las contraseñas personalizadas usan los validadores de Django. La contraseña de
volcan no aparece en código, documentación, fixtures ni archivos versionados.

Referencias:
- https://www.postgresql.org/download/windows/
- https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication
- https://docs.djangoproject.com/en/5.2/topics/auth/customizing/
