import re
import unicodedata

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from .models import Student, Teacher, User
from .permissions import accessible_universities


def letters(value):
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower())


def institutional_email(first_name, first_surname, second_surname, domain):
    names = first_name.split()[:2]
    normalized = [letters(name) for name in names]
    surnames = [letters(first_surname), letters(second_surname)]
    if not all(normalized) or not all(surnames):
        raise ValidationError({"names": "Los nombres y ambos apellidos deben contener letras válidas para el correo."})
    local = "".join(normalized) + "".join(name[0] for name in surnames)
    email = f"{local}@{domain}"
    try:
        validate_email(email)
    except DjangoValidationError:
        raise ValidationError({"email": "Los nombres producen un correo no válido o demasiado largo."})
    if len(local) > 64 or len(email) > 254:
        raise ValidationError({"email": "El correo generado es demasiado largo."})
    return email


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
    email = institutional_email(data["first_name"], data["first_surname"], data["second_surname"], university.email_domain)
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError({"email": "Este correo ya existe. Revisa los nombres; no se creó otra cuenta."})
    try:
        with transaction.atomic():
            user = User(
                username=email, email=email, role=data["role"], first_name=data["first_name"],
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
