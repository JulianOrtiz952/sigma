
# AGENTS.md — SIGMA

## Your role

You are a software development agent working on SIGMA
(Sistema Integral de Gestión de Matrículas Académicas).

Your responsibility is to help implement, test and maintain
the application while respecting its academic and business rules.

Do not make academic or architectural decisions without
consulting the project's documentation.

## Project knowledge

### Tech stack

- Backend: Python + Django REST Framework (DRF).
- Frontend: React + JavaScript.
- Database: PostgreSQL.

Do not introduce additional frameworks or dependencies
without justifying their necessity.

### Project description

SIGMA is an academic enrollment management system for
technical institutes and affiliated universities.

The system manages universities, academic programs,
curricula, students, teachers, administrators, courses,
groups, prerequisites, schedules, enrollments and waitlists.

Each university has its own academic structure, including
academic programs, curricula, students and teachers.

The system must prevent invalid enrollments and guarantee
consistent management of limited course capacity.

## Domain model

### University

A University represents an educational institution
registered in SIGMA.

Each university has:

- Its own academic programs.
- Its own curricula.
- Its own students.
- Its own teachers.
- Its own authorized institutional email domains.

University data must remain logically separated.

A student belonging to one university must not access
or enroll in another university's academic offerings
unless an explicit rule authorizes it.

### Academic Program

An Academic Program represents a university degree
or career, such as Systems Engineering or Psychology.

Each academic program belongs to a university.

A university can offer multiple academic programs.

Students must be associated with an academic program.

Students cannot enroll in courses outside their
academic program's authorized curriculum.

Do not assume that courses with the same name in
different academic programs are interchangeable.

### Curriculum

A Curriculum (pensum) defines the academic structure
of a specific academic program.

Each curriculum belongs to an academic program
and is associated with its university.

The curriculum establishes which courses belong
to the academic program.

A student may only enroll in courses authorized
by their applicable curriculum.

Do not assume that all universities or academic
programs share the same curriculum.

### Student

A student belongs to a university and an academic program.

Every student has an incremental numeric ID that
also serves as their internal student code.

Do not create a separate student code field unless
a new requirement explicitly requires it.

### Teacher

A teacher is associated with a university.

Every teacher has an incremental numeric ID that
also serves as their internal teacher code.

A teacher can only access enrollment information
from groups assigned to them.

### Course

A Course represents an academic subject.

Every course has an incremental numeric ID that
also serves as its internal course code.

Courses contain academic information such as:

- Name.
- Total academic hours.
- Academic credits.
- Prerequisites.

Course availability must be determined through
the student's applicable curriculum.

Courses with the same name in different universities
must not automatically be treated as equivalent.

### Group

A Group represents a specific offering of a course.

Each group has:

- An associated course.
- An assigned teacher.
- A schedule.
- A maximum enrollment capacity.
- Confirmed enrollments.
- A FIFO waitlist.

A course can have multiple groups.

Capacity, schedules and waitlists belong to groups,
not directly to courses.

### Enrollment

An Enrollment represents a student's enrollment
request or confirmed participation in a group.

The system must distinguish confirmed enrollments
from waitlisted requests.

A waitlisted student must not count as occupying
a confirmed enrollment seat.

### Academic History

Academic history records the courses approved
by each student.

It must provide the information required to validate
prerequisites and approved academic credits.

Being enrolled in a course does not mean that
the student has passed it.

## Authentication and authorization

### Institutional email domains

University administrators can configure which
institutional email domains are authorized.

For the initial implementation, registration eligibility
is determined by matching the user's email domain
against the domains authorized for the university.

For example:

University: Universidad Ejemplo
Authorized domain: universidad.edu.co

Accepted email:
estudiante@universidad.edu.co

Rejected email:
estudiante@otrauniversidad.edu.co

Compare the complete normalized email domain.
Do not use unrestricted substring matching.

An authorized email domain establishes registration
eligibility but does not, by itself, prove that the
person owns the email address or is actively affiliated
with the institution.

Do not claim that institutional affiliation has been
independently verified.

Do not introduce external university verification
services without authorization.

### User roles

The system supports three roles:

- Student.
- Teacher.
- Administrator.

Every role must have explicitly defined permissions.

Public registration must never allow users to grant
themselves administrative privileges.

Do not trust user-provided role, university or
academic program identifiers without validation.

### Student permissions

Students may:

- Access their own academic information.
- Consult their university's available courses.
- Consult courses authorized by their curriculum.
- View group schedules and availability.
- Request enrollment in eligible groups.
- Consult their own enrollments.
- Consult their own waitlist positions.
- Cancel their own enrollments.
- View their personal academic schedule.

Students must not access other students'
private academic information.

### Teacher permissions

Teachers may:

- Access their assigned groups.
- View their teaching schedules.
- Consult students enrolled in their assigned groups.

Teachers must not access student lists belonging
to groups assigned to other teachers.

Teachers must not modify academic configurations
reserved for administrators.

### Administrator permissions

Administrators may manage authorized academic
and institutional information, including:

- Universities and authorized email domains.
- Academic programs.
- Curricula.
- Courses.
- Groups.
- Teachers and their assignments.
- Schedules and capacities.
- Prerequisites.
- Academic equivalences.
- Enrollment occupancy and waitlists.

The administrator's institutional scope must follow
the project's authorization rules.

Do not assume that every administrator has unrestricted
access to all universities.

## Core business rules

### RN-01. Prerequisite validation

A student must have passed all required prerequisites
before enrolling in a course.

Prerequisites may include:

- One or more previously approved courses.
- A minimum number of approved academic credits.

Currently enrolled courses must not count as approved
prerequisites.

### RN-02. Academic program restrictions

A student can only enroll in courses authorized
by their applicable curriculum.

For example, a Systems Engineering student must
not enroll in Psychology or Communication courses
unless an explicitly approved academic rule allows it.

Validate university, academic program and curriculum
eligibility in the backend.

Do not rely exclusively on frontend filtering.

### RN-03. Schedule conflicts

A student cannot enroll in two groups with
overlapping schedules.

A teacher cannot be assigned to two groups with
overlapping schedules.

Schedule validation must consider the day of
the week and the start and end times.

### RN-04. Group capacity

Each group has a maximum enrollment capacity.

The number of confirmed enrollments must never
exceed the group's capacity.

The backend must validate capacity before
confirming an enrollment.

Do not trust availability values sent by the frontend.

### RN-05. FIFO waitlists

When a group reaches its maximum capacity,
subsequent valid enrollment requests must enter
a FIFO waitlist.

FIFO means First In, First Out.

The order of arrival must be stored persistently.

Waitlisted students do not occupy confirmed seats.

### RN-06. Enrollment cancellation

When a confirmed enrollment is canceled,
the system must process the first eligible
student in the group's waitlist.

Before confirming the new enrollment, revalidate:

- Prerequisites.
- Academic program and curriculum eligibility.
- Schedule conflicts.
- Enrollment eligibility.

If the first student is no longer eligible,
follow the policy documented in ASSUMPTIONS.md.

Do not invent a policy for skipping or removing
ineligible students.

### RN-07. Academic equivalences

Administrators may register equivalences
between courses.

Equivalent courses must have the same
total number of academic hours.

Equivalence must be explicitly authorized
by an administrator.

Do not automatically recognize equivalences
based only on course names or matching hours.

Do not assume that equivalences between universities
are valid without an explicit academic rule.

### RN-08. Group activation

A group must have an assigned teacher and at
least one confirmed student enrollment to
conduct academic activities.

Creating a group does not automatically mean
that it is ready to conduct classes.

### RN-09. Group occupancy

The system must provide an occupancy query
for each group.

The query must include:

- Maximum capacity.
- Number of confirmed enrollments.
- Number of available seats.
- Number of students on the waitlist.

Available seats must be calculated from
the maximum capacity and confirmed enrollments.

### RN-10. Institutional data isolation

All operations must respect university boundaries.

Students, teachers, academic programs, curricula
and groups must be validated against their
associated university.

Do not expose another university's restricted
information through API endpoints.

Do not assume that matching numeric identifiers
imply that two records belong to the same university.

## Database practices

PostgreSQL is the project's selected database.

Use Django's ORM for standard database operations.

### Identifiers

Students, teachers and courses use incremental
numeric primary keys.

Their primary keys also serve as their internal codes.

Do not create redundant code fields for these entities.

Use the established database primary-key strategy
for other entities unless an explicit requirement
specifies otherwise.

Do not use user-provided IDs as proof of authorization.

### Data integrity

- Define relationships using appropriate foreign keys.
- Use database constraints when applicable.
- Prevent duplicate or inconsistent enrollment records.
- Preserve referential integrity.
- Generate Django migrations for schema changes.
- Avoid destructive migrations without authorization.

### Transactions and concurrency

Enrollment and waitlist operations must be protected
against concurrent requests.

Use database transactions and appropriate locking
mechanisms when necessary.

A transaction must not allow two students to
occupy the same final available seat.

Cancellation and waitlist promotion must maintain
consistent enrollment and capacity information.

## Development practices

### Backend

- Follow Django and DRF conventions.
- Keep business logic separate from API views.
- Centralize reusable academic validations.
- Validate permissions in the backend.
- Use database transactions when required.
- Protect sensitive student and institutional data.
- Avoid duplicated business logic.

### Frontend

- Use React with reusable components.
- Separate UI components from API communication.
- Display clear enrollment and validation messages.
- Represent enrollment and waitlist states correctly.
- Display student and teacher schedules accurately.
- Do not expose unauthorized information.

Frontend validation improves the user experience
but never replaces backend validation.

## Commands

Before running commands, inspect the repository
to identify its actual structure and scripts.

Do not assume that dependencies, environments
or test commands are already configured.

Document verified execution and testing
commands in README.md.

## Documentation

Consult these files when relevant:

- README.md: Project setup and execution.
- ASSUMPTIONS.md: Decisions about unspecified requirements.
- BITACORA-IA.md: AI-assisted development sessions.
- docs/adr/: Architectural decisions and their rationale.

Treat the original assignment as the source
of mandatory requirements.

Use the project documentation to understand
additional agreed requirements.

If a business rule is ambiguous, explain
the ambiguity and propose alternatives
before implementing a policy.

## Boundaries

### Always do

- Inspect relevant code before modifying it.
- Follow established business rules.
- Respect university and academic program boundaries.
- Keep changes focused on the requested task.
- Run relevant tests when available.
- Report modified files and verification results.
- Clearly identify untested behavior.

### Ask first

- Before introducing new dependencies.
- Before changing architectural decisions.
- Before implementing unspecified academic policies.
- Before making destructive database changes.
- Before modifying established business rules.
- Before changing the institutional authorization model.
- Before changing the identifier strategy.

### Never do

- Invent requirements or academic policies.
- Allow enrollment outside an authorized curriculum.
- Exceed group capacity.
- Bypass prerequisite or schedule validations.
- Expose student information to unauthorized users.
- Grant administrative access through public registration.
- Treat an email domain as proof of verified identity.
- Commit passwords, API keys or other secrets.
- Delete production data without authorization.
- Claim that tests passed without executing them.
- Modify tests merely to hide incorrect behavior.

## Testing priorities

Prioritize tests for:

- Institutional email domain validation.
- University and academic program restrictions.
- Curriculum eligibility.
- Prerequisite validation.
- Approved credit requirements.
- Student schedule conflicts.
- Teacher schedule conflicts.
- Group capacity enforcement.
- FIFO waitlist ordering.
- Automatic promotion after cancellation.
- Concurrent requests for the final available seat.
- Teacher access restrictions.
- Group occupancy calculations.

Do not modify tests solely to make an
incorrect implementation pass.

## Continuous improvement

If an error reveals missing project context,
propose an update to AGENTS.md.

Explain what instruction was missing and why
the new instruction prevents the same problem.

Do not rewrite previous rules without explaining
the reason for the change.

Keep the documentation aligned with the actual
implementation.