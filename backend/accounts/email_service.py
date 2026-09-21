"""Generación y asignación de correos; el llamador mantiene el bloqueo institucional."""
import re
import unicodedata

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from .models import User


def letters(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", normalized.lower())


def institutional_email(first_name, first_surname, second_surname, domain):
    names = [letters(name) for name in first_name.split()[:2]]
    surnames = [letters(first_surname), letters(second_surname)]
    if not names or not all(names) or not all(surnames):
        raise ValidationError({"names": "Los nombres y ambos apellidos deben contener letras válidas para el correo."})
    local = "".join(names) + "".join(name[0] for name in surnames)
    return validate_candidate(local, domain)


def validate_candidate(local, domain):
    email = f"{local}@{domain}"
    if len(local) > 64 or len(email) > 254:
        raise ValidationError({"email": "El correo generado es demasiado largo; revisa los nombres."})
    try:
        validate_email(email)
    except DjangoValidationError:
        raise ValidationError({"email": "El correo generado no es válido."})
    return email


def allocate_email(base_email):
    """Usar dentro de transaction.atomic con select_for_update sobre University."""
    local, domain = base_email.rsplit("@", 1)
    candidate = base_email
    # El primer homónimo usa 2; el correo base representa implícitamente el 1.
    suffix = 1
    while User.objects.filter(Q(email__iexact=candidate) | Q(username=candidate)).exists():
        suffix += 1
        candidate = validate_candidate(f"{local}{suffix}", domain)
    return candidate
