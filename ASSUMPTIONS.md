# Decisiones y requisitos pendientes

## Acordado con el usuario — 2026-09-18

- `volcan` administra todas las universidades; es la excepción global explícita.
  Otros administradores son limitados por defecto a universidades asignadas.
- El registro (signup) es privado: solo la administración crea docentes y estudiantes.
  No hay autorregistro público ni creación de administradores desde la API.
- Los estudiantes requieren programa académico de su universidad. Se incluye
  creación de programas dentro de la sección Universidades.
- El ID incremental de cada perfil docente/estudiante es su código. No hay campo duplicado.
- La contraseña inicial por defecto es ese código; la administración puede indicar
  una contraseña personalizada, que se valida. Todas se guardan como hash.
- El correo se genera con los dos primeros nombres y las iniciales de ambos
  apellidos, seguido del dominio de la universidad seleccionada.

## Comportamiento técnico documentado

- Se convierten letras a minúsculas y se eliminan tildes para el correo. Un único
  nombre usa ese nombre; ambos apellidos son obligatorios en esta etapa.
- Correos repetidos se rechazan sin crear cuentas adicionales. La política de
  sufijos para homónimos queda pendiente, sin alterar nombres automáticamente.
- Una universidad tiene un dominio en esta primera interfaz. El dominio se
  normaliza y valida completo; no se aceptan rutas, @ ni coincidencias parciales.
- El correo generado es un identificador local. No crea buzones ni verifica
  propiedad del correo o afiliación institucional externa.
- Se utiliza sesión Django con cookies HttpOnly y CSRF. Docentes y estudiantes
  solo acceden a su propio perfil en esta etapa.

## Pendiente para ampliar matrículas

- Equivalencias académicas entre instituciones.
- Verificación de propiedad de correos y recuperación de cuentas.
- Historial administrable y equivalencias.

## Acordado con el usuario — 2026-09-21

- La administración crea materias asociadas al pensum vigente de un programa.
- Cada materia registra semestre, horas, créditos y prerrequisitos opcionales por
  materias y/o mínimo de créditos aprobados.
- Una materia prerrequisito debe ser del mismo pensum y de un semestre inferior.
- La oferta inicial se crea abierta, con exactamente un docente de la misma
  universidad y un cupo positivo definido por la administración.
- Los únicos solicitantes de cupo son estudiantes del programa correspondiente.
- Al agotarse el cupo, las solicitudes válidas se conservan en orden FIFO como
  lista de espera y no cuentan como matrículas confirmadas.
- Una oferta solo puede pasar a activa con docente y al menos un estudiante
  confirmado; también puede finalizarse.

## Decisiones técnicas de esta etapa

- Se conserva la separación del dominio documentado: la materia `Course` contiene
  información académica y el `Group` contiene docente, cupo, estado y ocupación.
  La interfaz los presenta juntos bajo “Cursos”.
- Mientras no exista una política de versiones históricas, cada programa tiene un
  único pensum vigente. Relajar esa restricción requiere una decisión explícita.
- Cada grupo admite uno o más bloques semanales con día, hora inicial y hora final.
- Si el primer estudiante en espera tiene un choque al liberarse un cupo, intercambia
  prioridad con el siguiente candidato, conserva su solicitud y recibe una
  notificación con materia, día e intervalo exacto del cruce.
- La promoción vuelve a validar pensum, prerrequisitos y créditos. Si se pierde
  elegibilidad académica, se conserva la posición, se notifica y la promoción se
  detiene: aún no se autorizó una política para saltar o retirar ese caso.
- Cancelar una matrícula confirmada retira inmediatamente sus bloques del horario
  personal y procesa la cola dentro de la misma transacción.

## Creación de correos

Cuando dos usuarios de una misma universidad generen el mismo correo institucional, el sistema añadirá un sufijo numérico incremental al identificador del correo, comenzando en 2, hasta obtener una dirección única.

Las reglas de AGENTS.md se conservan sin modificaciones.
