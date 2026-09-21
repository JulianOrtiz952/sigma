from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from .models import Student, Teacher, University, User
from .email_service import allocate_email, institutional_email
from .permissions import accessible_universities


def create_account(actor, data):
    university = data["university"]
    if not accessible_universities(actor).filter(pk=university.pk).exists():
        raise ValidationError({"university": "Universidad no autorizada."})
    program = data.get("academic_program")
    if data["role"] == User.Role.STUDENT:
        if program is None or program.university_id != university.pk:
            raise ValidationError({"academic_program": "Selecciona un programa de la universidad indicada."})
    elif program is not None:
        raise ValidationError({"academic_program": "Los docentes no requieren un programa académico."})
    try:
        with transaction.atomic():
            # Serializa las altas de la misma institución, incluso entre procesos.
            university = University.objects.select_for_update().get(pk=university.pk)
            email = allocate_email(institutional_email(data["first_name"], data["first_surname"], data["second_surname"], university.email_domain))
            user = User(
                username=email, email=email, role=data["role"], first_name=data["first_name"],
                must_change_password=True,
                first_surname=data["first_surname"], second_surname=data["second_surname"],
                last_name=f'{data["first_surname"]} {data["second_surname"]}',
            )
            user.set_unusable_password()
            user.save()
            if user.role == User.Role.STUDENT:
                profile = Student.objects.create(user=user, academic_program=program)
            else:
                profile = Teacher.objects.create(user=user, university=university)
            password = data.get("password") or str(profile.pk)
            if data.get("password"):
                try:
                    validate_password(password, user=user)
                except DjangoValidationError as exc:
                    raise ValidationError({"password": exc.messages})
            user.set_password(password)
            user.save(update_fields=["password"])
            return user
    except IntegrityError:
        raise ValidationError({"email": "No se pudo crear la cuenta; el correo ya está registrado."})
