"""Validación y cambio transaccional de contraseña, sin responsabilidades HTTP."""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import User


@transaction.atomic
def change_password(user, current_password, new_password, confirm_password):
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if not locked_user.check_password(current_password):
        raise ValidationError({"current_password": "La contraseña actual es incorrecta."})
    if new_password != confirm_password:
        raise ValidationError({"confirm_password": "Las contraseñas nuevas no coinciden."})
    if locked_user.check_password(new_password):
        raise ValidationError({"new_password": "La nueva contraseña debe ser diferente a la actual."})
    try:
        validate_password(new_password, user=locked_user)
    except DjangoValidationError as exc:
        raise ValidationError({"new_password": exc.messages})
    locked_user.set_password(new_password)
    locked_user.must_change_password = False
    locked_user.password_changed_at = timezone.now()
    locked_user.save(update_fields=["password", "must_change_password", "password_changed_at"])
    return locked_user
