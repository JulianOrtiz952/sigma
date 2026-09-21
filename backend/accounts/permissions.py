from rest_framework.permissions import BasePermission
from .models import Administrator, University


def administrator_for(user):
    if not user.is_authenticated or user.role != "administrator":
        return None
    return Administrator.objects.filter(user=user).first()


def accessible_universities(user):
    administrator = administrator_for(user)
    if administrator is None:
        return University.objects.none()
    return University.objects.all() if administrator.is_global else administrator.universities.all()


class IsAdministrator(BasePermission):
    message = "Esta acción requiere una cuenta administradora."

    def has_permission(self, request, view):
        return administrator_for(request.user) is not None


class IsStudent(BasePermission):
    message = "Esta acción requiere una cuenta estudiantil."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "student" and hasattr(request.user, "student")
