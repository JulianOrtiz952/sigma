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
