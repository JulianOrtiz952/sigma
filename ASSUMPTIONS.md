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

## Pendiente antes de implementar matrículas

- Política para el primer estudiante no elegible en la lista de espera (RN-06).
- Equivalencias académicas entre instituciones.
- Verificación de propiedad de correos y recuperación de cuentas.
- Currículos, cursos, grupos, horarios y matrículas.

## Creación de correos

Cuando dos usuarios de una misma universidad generen el mismo correo institucional, el sistema añadirá un sufijo numérico incremental al identificador del correo, comenzando en 2, hasta obtener una dirección única.

Las reglas de AGENTS.md se conservan sin modificaciones.
