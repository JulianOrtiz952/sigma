from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied


class PasswordGateSessionAuthentication(SessionAuthentication):
    """Impide saltarse el primer cambio incluso en vistas públicas con sesión."""
    allowed_views = {"account-session", "account-login", "account-logout", "account-password"}

    def authenticate(self, request):
        result = super().authenticate(request)
        if result:
            user, _ = result
            match = request.resolver_match
            if user.requires_password_change and (not match or match.url_name not in self.allowed_views):
                raise PermissionDenied({"detail": "Debes cambiar tu contraseña inicial antes de continuar.", "code": "password_change_required"})
        return result
