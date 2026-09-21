import re

from django.db import models
from rest_framework import serializers
from .models import (
    AcademicProgram,
    Course,
    Curriculum,
    Enrollment,
    Group,
    GroupSchedule,
    Teacher,
    University,
    User,
)
from .academic_service import student_blocks_conflict, teacher_schedule_conflict, validate_schedule_blocks
from .permissions import accessible_universities, administrator_for


class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ["id", "name", "email_domain"]

    def validate_name(self, value):
        value = " ".join(value.split())
        if University.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Esta universidad ya está afiliada.")
        return value

    def validate_email_domain(self, value):
        value = value.strip().lower()
        try:
            value = value.encode("idna").decode("ascii")
        except UnicodeError:
            raise serializers.ValidationError("Dominio no válido.")
        labels = value.split(".")
        if len(value) > 253 or len(labels) < 2 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels) or not re.fullmatch(r"[a-z]{2,63}", labels[-1]):
            raise serializers.ValidationError("Escribe solo el dominio, por ejemplo ufps.edu.co; sin @ ni https://.")
        if University.objects.filter(email_domain=value).exists():
            raise serializers.ValidationError("Este dominio ya está registrado.")
        return value


class ProgramSerializer(serializers.ModelSerializer):
    curriculum = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AcademicProgram
        fields = ["id", "name", "university", "curriculum"]

    def get_curriculum(self, obj):
        curriculum = getattr(obj, "curriculum", None)
        return {"id": curriculum.pk, "name": curriculum.name} if curriculum else None

    def validate(self, attrs):
        if not accessible_universities(self.context["request"].user).filter(pk=attrs["university"].pk).exists():
            raise serializers.ValidationError({"university": "Universidad no autorizada."})
        attrs["name"] = " ".join(attrs["name"].split())
        if AcademicProgram.objects.filter(university=attrs["university"], name__iexact=attrs["name"]).exists():
            raise serializers.ValidationError({"name": "Este programa ya existe en la universidad."})
        return attrs

    def create(self, validated_data):
        program = super().create(validated_data)
        Curriculum.objects.create(academic_program=program, name=f"Pensum de {program.name}")
        return program


class ScheduleBlockSerializer(serializers.Serializer):
    day_of_week = serializers.ChoiceField(choices=GroupSchedule.Day.choices)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()


def next_group_section(course):
    used = set(course.groups.values_list("section", flat=True))
    number = 0
    while True:
        value, current = "", number
        while True:
            current, remainder = divmod(current, 26)
            value = chr(65 + remainder) + value
            if current == 0:
                break
            current -= 1
        if value not in used:
            return value
        number += 1


def validate_group_configuration(course, teacher, schedules):
    if teacher.university_id != course.curriculum.university.pk:
        raise serializers.ValidationError({"teacher": "El docente debe pertenecer a la misma universidad del pensum."})
    validate_schedule_blocks(schedules)
    conflict = teacher_schedule_conflict(teacher, schedules)
    if conflict:
        day = GroupSchedule.Day(conflict.day_of_week).label
        raise serializers.ValidationError({
            "schedules": f"El docente ya tiene {conflict.group.course.name} {conflict.group.section} el {day} de {conflict.start_time:%H:%M} a {conflict.end_time:%H:%M}."
        })


def create_group(course, teacher, capacity, schedules):
    signature = {(item["day_of_week"], item["start_time"], item["end_time"]) for item in schedules}
    for existing in course.groups.prefetch_related("schedules"):
        existing_signature = {(item.day_of_week, item.start_time, item.end_time) for item in existing.schedules.all()}
        if signature == existing_signature:
            raise serializers.ValidationError({"schedules": "Ya existe un grupo de esta materia con el mismo horario."})
    group = Group.objects.create(course=course, section=next_group_section(course), teacher=teacher, capacity=capacity)
    GroupSchedule.objects.bulk_create([GroupSchedule(group=group, **block) for block in schedules])
    return group


class GroupCreateSerializer(serializers.Serializer):
    teacher = serializers.PrimaryKeyRelatedField(queryset=Teacher.objects.select_related("university", "user"))
    capacity = serializers.IntegerField(min_value=1)
    schedules = ScheduleBlockSerializer(many=True)

    def validate(self, attrs):
        validate_group_configuration(self.context["course"], attrs["teacher"], attrs["schedules"])
        return attrs

    def create(self, validated_data):
        return create_group(self.context["course"], **validated_data)


class GroupUpdateSerializer(GroupCreateSerializer):
    def validate(self, attrs):
        group = self.context["group"]
        if attrs["teacher"].university_id != group.course.curriculum.university.pk:
            raise serializers.ValidationError({"teacher": "El docente debe pertenecer a la misma universidad del pensum."})
        confirmed = group.enrollments.filter(status=Enrollment.Status.CONFIRMED).count()
        if attrs["capacity"] < confirmed:
            raise serializers.ValidationError({"capacity": f"El cupo no puede ser menor que las {confirmed} matrículas confirmadas."})
        validate_schedule_blocks(attrs["schedules"])
        conflict = teacher_schedule_conflict(attrs["teacher"], attrs["schedules"], exclude_group_id=group.pk)
        if conflict:
            day = GroupSchedule.Day(conflict.day_of_week).label
            raise serializers.ValidationError({
                "schedules": f"El docente ya tiene {conflict.group.course.name} {conflict.group.section} el {day} de {conflict.start_time:%H:%M} a {conflict.end_time:%H:%M}."
            })
        confirmed_students = group.enrollments.filter(status=Enrollment.Status.CONFIRMED).select_related("student__user")
        for enrollment in confirmed_students:
            student_conflict = student_blocks_conflict(enrollment.student, attrs["schedules"], exclude_group_id=group.pk)
            if student_conflict:
                target, existing = student_conflict
                day = GroupSchedule.Day(target.day_of_week).label
                raise serializers.ValidationError({
                    "schedules": f"El cambio cruza el horario de {enrollment.student.user.get_full_name()} con {existing.group.course.name} {existing.group.section} el {day}."
                })
        return attrs

    def update(self, instance, validated_data):
        instance.teacher = validated_data["teacher"]
        instance.capacity = validated_data["capacity"]
        instance.save(update_fields=["teacher", "capacity"])
        instance.schedules.all().delete()
        GroupSchedule.objects.bulk_create([GroupSchedule(group=instance, **block) for block in validated_data["schedules"]])
        return instance


class CourseCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    curriculum = serializers.PrimaryKeyRelatedField(queryset=Curriculum.objects.select_related("academic_program__university"))
    academic_hours = serializers.IntegerField(min_value=1)
    credits = serializers.IntegerField(min_value=1)
    semester = serializers.IntegerField(min_value=1)
    minimum_approved_credits = serializers.IntegerField(min_value=0, default=0)
    prerequisites = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(), many=True, required=False)
    teacher = serializers.PrimaryKeyRelatedField(queryset=Teacher.objects.select_related("university", "user"))
    capacity = serializers.IntegerField(min_value=1)
    schedules = ScheduleBlockSerializer(many=True)

    def validate(self, attrs):
        curriculum = attrs["curriculum"]
        university = curriculum.university
        if not accessible_universities(self.context["request"].user).filter(pk=university.pk).exists():
            raise serializers.ValidationError({"curriculum": "Pensum no autorizado."})
        attrs["name"] = " ".join(attrs["name"].split())
        if Course.objects.filter(curriculum=curriculum, name__iexact=attrs["name"]).exists():
            raise serializers.ValidationError({"name": "Esta materia ya existe. Puedes crear automáticamente el siguiente grupo con otro horario."})
        prerequisites = attrs.get("prerequisites", [])
        invalid = [course.pk for course in prerequisites if course.curriculum_id != curriculum.pk or course.semester >= attrs["semester"]]
        if invalid:
            raise serializers.ValidationError({
                "prerequisites": "Cada materia prerrequisito debe pertenecer al mismo pensum y a un semestre inferior."
            })
        placeholder = type("CourseUniversity", (), {"curriculum": curriculum})
        validate_group_configuration(placeholder, attrs["teacher"], attrs["schedules"])
        return attrs

    def create(self, validated_data):
        prerequisites = validated_data.pop("prerequisites", [])
        teacher = validated_data.pop("teacher")
        capacity = validated_data.pop("capacity")
        schedules = validated_data.pop("schedules")
        course = Course.objects.create(**validated_data)
        course.prerequisites.set(prerequisites)
        create_group(course, teacher, capacity, schedules)
        return course


def schedule_data(schedule):
    return {
        "id": schedule.pk,
        "day_of_week": schedule.day_of_week,
        "day": schedule.get_day_of_week_display(),
        "start_time": schedule.start_time.strftime("%H:%M"),
        "end_time": schedule.end_time.strftime("%H:%M"),
    }


def group_data(group, student=None):
    enrollment = None
    waitlist_position = None
    if student:
        enrollment = group.enrollments.filter(student=student).exclude(status=Enrollment.Status.CANCELLED).first()
        if enrollment and enrollment.status == Enrollment.Status.WAITLISTED:
            waitlist_position = group.enrollments.filter(
                status=Enrollment.Status.WAITLISTED,
                queue_order__lt=enrollment.queue_order,
            ).count() + 1
    return {
        "id": group.pk,
        "section": group.section,
        "display_name": f"{group.course.name} {group.section}",
        "teacher": group.teacher_id,
        "teacher_name": group.teacher.user.get_full_name(),
        "capacity": group.capacity,
        "status": group.status,
        "confirmed": group.confirmed_count,
        "available_seats": max(group.capacity - group.confirmed_count, 0),
        "waitlist": group.waitlist_count,
        "schedules": [schedule_data(item) for item in group.schedules.all()],
        "enrollment": None if enrollment is None else {
            "id": enrollment.pk,
            "status": enrollment.status,
            "waitlist_position": waitlist_position,
        },
    }


def course_data(course, student=None):
    groups = course.groups.select_related("teacher__user").prefetch_related("schedules").annotate(
        confirmed_count=models.Count("enrollments", filter=models.Q(enrollments__status=Enrollment.Status.CONFIRMED)),
        waitlist_count=models.Count("enrollments", filter=models.Q(enrollments__status=Enrollment.Status.WAITLISTED)),
    ).order_by("section")
    return {
        "id": course.pk,
        "code": course.pk,
        "name": course.name,
        "academic_hours": course.academic_hours,
        "credits": course.credits,
        "semester": course.semester,
        "minimum_approved_credits": course.minimum_approved_credits,
        "curriculum": course.curriculum_id,
        "program": course.curriculum.academic_program.name,
        "university": course.curriculum.university.name,
        "prerequisites": [
            {"id": item.pk, "name": item.name, "semester": item.semester}
            for item in course.prerequisites.all()
        ],
        "groups": [group_data(group, student=student) for group in groups],
    }


class UserCreateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[User.Role.TEACHER, User.Role.STUDENT])
    first_name = serializers.CharField(max_length=150)
    first_surname = serializers.CharField(max_length=100)
    second_surname = serializers.CharField(max_length=100)
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all())
    academic_program = serializers.PrimaryKeyRelatedField(queryset=AcademicProgram.objects.all(), required=False, allow_null=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=128, trim_whitespace=False)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({"detail": "El formulario contiene campos no permitidos."})
        return super().to_internal_value(data)

    def validate(self, attrs):
        for key in ["first_name", "first_surname", "second_surname"]:
            attrs[key] = " ".join(attrs[key].split())
        if len(f'{attrs["first_surname"]} {attrs["second_surname"]}') > 150:
            raise serializers.ValidationError({"last_name": "Los apellidos son demasiado largos."})
        return attrs


def user_data(user):
    result = {"id": user.pk, "username": user.username, "email": user.email, "first_name": user.first_name,
              "first_surname": user.first_surname, "second_surname": user.second_surname, "role": user.role,
              "code": None, "university": None, "academic_program": None, "is_global_admin": False}
    result.update(must_change_password=user.requires_password_change,
                  university_domain=None, is_active=user.is_active,
                  date_joined=user.date_joined.isoformat(),
                  password_changed_at=user.password_changed_at.isoformat() if user.password_changed_at else None)
    if user.role == User.Role.STUDENT:
        profile = user.student
        result.update(code=profile.pk, university=profile.university.name, academic_program=profile.academic_program.name)
        result["university_domain"] = profile.university.email_domain
    elif user.role == User.Role.TEACHER:
        profile = user.teacher
        result.update(code=profile.pk, university=profile.university.name)
        result["university_domain"] = profile.university.email_domain
    else:
        administrator = administrator_for(user)
        result["is_global_admin"] = bool(administrator and administrator.is_global)
    return result


def session_user_data(user):
    if user.requires_password_change:
        return {"id": user.pk, "first_name": user.first_name, "role": user.role, "must_change_password": True}
    return user_data(user)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    confirm_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
