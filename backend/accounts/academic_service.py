from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import AcademicRecord, Enrollment, Group, GroupSchedule, Notification


def blocks_overlap(first, second):
    return first.day_of_week == second.day_of_week and first.start_time < second.end_time and second.start_time < first.end_time


def validate_schedule_blocks(blocks):
    if not blocks:
        raise ValidationError({"schedules": "Añade al menos un bloque semanal."})
    for index, block in enumerate(blocks):
        if block["start_time"] >= block["end_time"]:
            raise ValidationError({"schedules": f"El bloque {index + 1} debe terminar después de comenzar."})
        candidate = type("Block", (), block)
        for previous in blocks[:index]:
            if blocks_overlap(candidate, type("Block", (), previous)):
                raise ValidationError({"schedules": "Los bloques del mismo grupo no pueden superponerse."})


def teacher_schedule_conflict(teacher, blocks, exclude_group_id=None):
    existing = GroupSchedule.objects.filter(group__teacher=teacher).exclude(
        group__status=Group.Status.FINISHED
    ).select_related("group__course")
    if exclude_group_id:
        existing = existing.exclude(group_id=exclude_group_id)
    for block in blocks:
        candidate = type("Block", (), block)
        for scheduled in existing:
            if blocks_overlap(candidate, scheduled):
                return scheduled
    return None


def enrollment_ineligibility(student, course):
    if student.academic_program_id != course.curriculum.academic_program_id:
        return "La materia no pertenece al pensum de tu programa académico."
    approved = AcademicRecord.objects.filter(student=student, course__curriculum__academic_program=student.academic_program)
    approved_ids = set(approved.values_list("course_id", flat=True))
    missing = [item.name for item in course.prerequisites.all() if item.pk not in approved_ids]
    if missing:
        return f"Debes aprobar primero: {', '.join(missing)}."
    approved_credits = approved.aggregate(total=Sum("course__credits"))["total"] or 0
    if approved_credits < course.minimum_approved_credits:
        return f"Debes tener al menos {course.minimum_approved_credits} créditos aprobados."
    return None


def student_schedule_conflict(student, group):
    return student_blocks_conflict(student, list(group.schedules.all()), exclude_group_id=group.pk)


def student_blocks_conflict(student, blocks, exclude_group_id=None):
    existing = GroupSchedule.objects.filter(
        group__enrollments__student=student,
        group__enrollments__status=Enrollment.Status.CONFIRMED,
    ).exclude(group__status=Group.Status.FINISHED).select_related("group__course")
    if exclude_group_id:
        existing = existing.exclude(group_id=exclude_group_id)
    for block in blocks:
        target = block if hasattr(block, "day_of_week") else type("Block", (), block)
        for scheduled in existing:
            if blocks_overlap(target, scheduled):
                return target, scheduled
    return None


def conflict_message(group, conflict):
    target, existing = conflict
    day = GroupSchedule.Day(target.day_of_week).label
    overlap_start = max(target.start_time, existing.start_time)
    overlap_end = min(target.end_time, existing.end_time)
    return (
        f"No se pudo asignar el cupo de {group.course.name} {group.section} porque cruza con "
        f"{existing.group.course.name} {existing.group.section} el {day}, "
        f"de {overlap_start.strftime('%H:%M')} a {overlap_end.strftime('%H:%M')}."
    )


def _next_queue_order(group):
    maximum = group.enrollments.filter(status=Enrollment.Status.WAITLISTED).aggregate(value=Max("queue_order"))["value"] or 0
    return maximum + 1


@transaction.atomic
def request_enrollment(student, group_id):
    group = Group.objects.select_for_update().select_related(
        "course__curriculum__academic_program"
    ).prefetch_related("course__prerequisites", "schedules").get(pk=group_id)
    if group.status == Group.Status.FINISHED:
        raise ValidationError({"detail": "Este grupo ya finalizó y no admite matrículas."})
    if not group.schedules.exists():
        raise ValidationError({"detail": "Este grupo aún no tiene un horario definido por la administración."})
    reason = enrollment_ineligibility(student, group.course)
    if reason:
        raise ValidationError({"detail": reason})
    if Enrollment.objects.select_for_update().filter(
        student=student, group__course=group.course,
        status__in=[Enrollment.Status.CONFIRMED, Enrollment.Status.WAITLISTED],
    ).exclude(group=group).exists():
        raise ValidationError({"detail": "Ya tienes una matrícula o solicitud para otro grupo de esta materia."})
    enrollment = Enrollment.objects.select_for_update().filter(group=group, student=student).first()
    if enrollment and enrollment.status != Enrollment.Status.CANCELLED:
        raise ValidationError({"detail": "Ya tienes una solicitud para este grupo."})
    confirmed = group.enrollments.filter(status=Enrollment.Status.CONFIRMED).count()
    if confirmed < group.capacity:
        conflict = student_schedule_conflict(student, group)
        if conflict:
            raise ValidationError({"detail": conflict_message(group, conflict)})
        new_status, queue_order = Enrollment.Status.CONFIRMED, None
    else:
        new_status, queue_order = Enrollment.Status.WAITLISTED, _next_queue_order(group)
    if enrollment:
        enrollment.status, enrollment.queue_order, enrollment.requested_at = new_status, queue_order, timezone.now()
        enrollment.save(update_fields=["status", "queue_order", "requested_at"])
    else:
        enrollment = Enrollment.objects.create(group=group, student=student, status=new_status, queue_order=queue_order)
    return enrollment


def _swap_with_next_candidate(group, candidate, examined_ids):
    next_candidate = group.enrollments.filter(status=Enrollment.Status.WAITLISTED).exclude(
        pk__in=examined_ids
    ).order_by("queue_order", "requested_at", "id").first()
    if not next_candidate:
        return False
    temporary = _next_queue_order(group)
    original_order, next_order = candidate.queue_order, next_candidate.queue_order
    candidate.queue_order = temporary
    candidate.save(update_fields=["queue_order"])
    next_candidate.queue_order = original_order
    next_candidate.save(update_fields=["queue_order"])
    candidate.queue_order = next_order
    candidate.save(update_fields=["queue_order"])
    return True


def _notify(user, title, message):
    Notification.objects.create(user=user, title=title, message=message)


def promote_waitlist(group):
    examined_ids = set()
    while True:
        candidate = group.enrollments.select_for_update().filter(
            status=Enrollment.Status.WAITLISTED
        ).exclude(pk__in=examined_ids).select_related("student__user").order_by("queue_order", "requested_at", "id").first()
        if not candidate:
            return None
        examined_ids.add(candidate.pk)
        reason = enrollment_ineligibility(candidate.student, group.course)
        if reason:
            _notify(candidate.student.user, "No fue posible asignar tu cupo", f"{group.course.name} {group.section}: {reason}")
            # No existe una política autorizada para saltar o retirar a quien
            # perdió elegibilidad académica. Conserva su lugar y se detiene.
            return None
        conflict = student_schedule_conflict(candidate.student, group)
        if conflict:
            _notify(candidate.student.user, "Choque de horario al asignar un cupo", conflict_message(group, conflict))
            if not _swap_with_next_candidate(group, candidate, examined_ids):
                return None
            continue
        candidate.status, candidate.queue_order = Enrollment.Status.CONFIRMED, None
        candidate.save(update_fields=["status", "queue_order"])
        _notify(candidate.student.user, "Cupo asignado", f"Tu matrícula en {group.course.name} {group.section} fue confirmada desde la lista de espera.")
        return candidate


@transaction.atomic
def cancel_enrollment(student, enrollment_id):
    enrollment = Enrollment.objects.select_for_update().select_related("group__course").filter(
        pk=enrollment_id, student=student
    ).first()
    if not enrollment:
        raise ValidationError({"detail": "Matrícula no encontrada."})
    if enrollment.status == Enrollment.Status.CANCELLED:
        raise ValidationError({"detail": "Esta matrícula ya fue cancelada."})
    group = Group.objects.select_for_update().prefetch_related("course__prerequisites", "schedules").get(pk=enrollment.group_id)
    was_confirmed = enrollment.status == Enrollment.Status.CONFIRMED
    enrollment.status, enrollment.queue_order = Enrollment.Status.CANCELLED, None
    enrollment.save(update_fields=["status", "queue_order"])
    promoted = promote_waitlist(group) if was_confirmed else None
    if was_confirmed and group.status == Group.Status.ACTIVE and not group.enrollments.filter(status=Enrollment.Status.CONFIRMED).exists():
        group.status = Group.Status.OPEN
        group.save(update_fields=["status"])
    return enrollment, promoted, was_confirmed


@transaction.atomic
def change_group_status(group_id, new_status):
    group = Group.objects.select_for_update().select_related("teacher").get(pk=group_id)
    if new_status not in {choice for choice, _ in Group.Status.choices}:
        raise ValidationError({"status": "Estado de grupo no válido."})
    if new_status == Group.Status.ACTIVE:
        if not group.teacher_id:
            raise ValidationError({"status": "Un grupo activo debe tener un docente."})
        if not group.schedules.exists():
            raise ValidationError({"status": "Un grupo activo debe tener al menos un bloque horario."})
        if not group.enrollments.filter(status=Enrollment.Status.CONFIRMED).exists():
            raise ValidationError({"status": "Un grupo activo debe tener al menos un estudiante confirmado."})
    group.status = new_status
    group.save(update_fields=["status"])
    return group
