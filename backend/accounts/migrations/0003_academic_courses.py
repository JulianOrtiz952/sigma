import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models


def create_curricula_for_existing_programs(apps, schema_editor):
    AcademicProgram = apps.get_model("accounts", "AcademicProgram")
    Curriculum = apps.get_model("accounts", "Curriculum")
    Curriculum.objects.bulk_create([
        Curriculum(academic_program=program, name=f"Pensum de {program.name}")
        for program in AcademicProgram.objects.all()
    ])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_user_must_change_password_user_password_changed_at")]

    operations = [
        migrations.CreateModel(
            name="Curriculum",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Pensum vigente", max_length=150)),
                ("academic_program", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="curriculum", to="accounts.academicprogram")),
            ],
            options={"ordering": ["academic_program__university__name", "academic_program__name"]},
        ),
        migrations.RunPython(create_curricula_for_existing_programs, migrations.RunPython.noop),
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("academic_hours", models.PositiveIntegerField()),
                ("credits", models.PositiveSmallIntegerField()),
                ("semester", models.PositiveSmallIntegerField()),
                ("minimum_approved_credits", models.PositiveIntegerField(default=0)),
                ("curriculum", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="courses", to="accounts.curriculum")),
                ("prerequisites", models.ManyToManyField(blank=True, related_name="required_by", symmetrical=False, to="accounts.course")),
            ],
            options={
                "ordering": ["curriculum_id", "semester", "name", "id"],
                "constraints": [
                    models.UniqueConstraint(django.db.models.functions.text.Lower("name"), models.F("curriculum"), name="course_name_per_curriculum_unique"),
                    models.CheckConstraint(condition=models.Q(("academic_hours__gt", 0)), name="course_positive_hours"),
                    models.CheckConstraint(condition=models.Q(("credits__gt", 0)), name="course_positive_credits"),
                    models.CheckConstraint(condition=models.Q(("semester__gt", 0)), name="course_positive_semester"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Group",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("capacity", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("open", "Abierto"), ("active", "Activo"), ("finished", "Finalizado")], default="open", max_length=10)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="groups", to="accounts.course")),
                ("teacher", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="groups", to="accounts.teacher")),
            ],
            options={
                "ordering": ["course__name", "id"],
                "constraints": [models.CheckConstraint(condition=models.Q(("capacity__gt", 0)), name="group_positive_capacity")],
            },
        ),
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("confirmed", "Confirmada"), ("waitlisted", "En lista de espera"), ("cancelled", "Cancelada")], max_length=12)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enrollments", to="accounts.group")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enrollments", to="accounts.student")),
            ],
            options={
                "ordering": ["requested_at", "id"],
                "constraints": [models.UniqueConstraint(fields=("group", "student"), name="one_enrollment_per_student_group")],
            },
        ),
        migrations.CreateModel(
            name="AcademicRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("approved_at", models.DateField()),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approved_records", to="accounts.course")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_records", to="accounts.student")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("student", "course"), name="one_approved_record_per_course")]},
        ),
    ]
