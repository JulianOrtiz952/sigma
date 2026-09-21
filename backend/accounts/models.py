from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class University(models.Model):
    name = models.CharField(max_length=150)
    email_domain = models.CharField(max_length=253, unique=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [models.UniqueConstraint(Lower("name"), name="university_name_ci_unique")]

    def __str__(self):
        return self.name


class AcademicProgram(models.Model):
    university = models.ForeignKey(University, on_delete=models.PROTECT, related_name="programs")
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ["name", "id"]
        constraints = [models.UniqueConstraint(Lower("name"), "university", name="program_name_per_university_unique")]


class Curriculum(models.Model):
    """Pensum vigente de un programa académico.

    La relación uno-a-uno conserva, por ahora, un único pensum aplicable por
    programa. Si el proyecto incorpora versiones históricas, esa decisión debe
    documentarse antes de relajar esta restricción.
    """

    academic_program = models.OneToOneField(
        AcademicProgram, on_delete=models.PROTECT, related_name="curriculum"
    )
    name = models.CharField(max_length=150, default="Pensum vigente")

    class Meta:
        ordering = ["academic_program__university__name", "academic_program__name"]

    @property
    def university(self):
        return self.academic_program.university


class Course(models.Model):
    # La clave primaria incremental también es el código interno de la materia.
    curriculum = models.ForeignKey(Curriculum, on_delete=models.PROTECT, related_name="courses")
    name = models.CharField(max_length=150)
    academic_hours = models.PositiveIntegerField()
    credits = models.PositiveSmallIntegerField()
    semester = models.PositiveSmallIntegerField()
    minimum_approved_credits = models.PositiveIntegerField(default=0)
    prerequisites = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="required_by")

    class Meta:
        ordering = ["curriculum_id", "semester", "name", "id"]
        constraints = [
            models.UniqueConstraint(Lower("name"), "curriculum", name="course_name_per_curriculum_unique"),
            models.CheckConstraint(condition=models.Q(academic_hours__gt=0), name="course_positive_hours"),
            models.CheckConstraint(condition=models.Q(credits__gt=0), name="course_positive_credits"),
            models.CheckConstraint(condition=models.Q(semester__gt=0), name="course_positive_semester"),
        ]


class Group(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Abierto"
        ACTIVE = "active", "Activo"
        FINISHED = "finished", "Finalizado"

    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="groups")
    section = models.CharField(max_length=3, default="A")
    teacher = models.ForeignKey("Teacher", on_delete=models.PROTECT, related_name="groups")
    capacity = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    class Meta:
        ordering = ["course__name", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(capacity__gt=0), name="group_positive_capacity"),
            models.UniqueConstraint(fields=["course", "section"], name="group_section_per_course_unique"),
        ]


class GroupSchedule(models.Model):
    class Day(models.IntegerChoices):
        MONDAY = 0, "Lunes"
        TUESDAY = 1, "Martes"
        WEDNESDAY = 2, "Miércoles"
        THURSDAY = 3, "Jueves"
        FRIDAY = 4, "Viernes"
        SATURDAY = 5, "Sábado"
        SUNDAY = 6, "Domingo"

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="schedules")
    day_of_week = models.PositiveSmallIntegerField(choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["day_of_week", "start_time", "end_time", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(start_time__lt=models.F("end_time")), name="schedule_start_before_end"),
            models.UniqueConstraint(fields=["group", "day_of_week", "start_time", "end_time"], name="unique_group_schedule_block"),
        ]


class Enrollment(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmada"
        WAITLISTED = "waitlisted", "En lista de espera"
        CANCELLED = "cancelled", "Cancelada"

    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="enrollments")
    student = models.ForeignKey("Student", on_delete=models.PROTECT, related_name="enrollments")
    status = models.CharField(max_length=12, choices=Status.choices)
    requested_at = models.DateTimeField(auto_now_add=True)
    queue_order = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["queue_order", "requested_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["group", "student"], name="one_enrollment_per_student_group"),
            models.UniqueConstraint(
                fields=["group", "queue_order"],
                condition=models.Q(status="waitlisted"),
                name="unique_waitlist_order_per_group",
            ),
        ]


class Notification(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=150)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class AcademicRecord(models.Model):
    """Materia aprobada; una matrícula activa nunca crea este registro."""

    student = models.ForeignKey("Student", on_delete=models.PROTECT, related_name="academic_records")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="approved_records")
    approved_at = models.DateField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "course"], name="one_approved_record_per_course")]


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMINISTRATOR = "administrator", "Administrador"
        TEACHER = "teacher", "Docente"
        STUDENT = "student", "Estudiante"

    username = models.CharField(max_length=254, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    first_surname = models.CharField(max_length=100, blank=True)
    second_surname = models.CharField(max_length=100, blank=True)
    must_change_password = models.BooleanField(default=False)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    @property
    def requires_password_change(self):
        return self.role in (self.Role.STUDENT, self.Role.TEACHER) and self.must_change_password

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower() if self.email else None
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_ci_unique"),
            models.CheckConstraint(condition=models.Q(role__in=["administrator", "teacher", "student"]), name="user_valid_role"),
        ]


class Administrator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="administrator")
    is_global = models.BooleanField(default=False)
    universities = models.ManyToManyField(University, blank=True, related_name="administrators")


class Teacher(models.Model):
    # La clave primaria incremental es el código; no se duplica en otro campo.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher")
    university = models.ForeignKey(University, on_delete=models.PROTECT, related_name="teachers")


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student")
    # La universidad se deriva del programa para impedir asignaciones inconsistentes.
    academic_program = models.ForeignKey(AcademicProgram, on_delete=models.PROTECT, related_name="students")

    @property
    def university(self):
        return self.academic_program.university
