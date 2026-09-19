from django.urls import path
from .views import LoginView, LogoutView, ProgramsView, SessionView, UniversitiesView, UsersView

urlpatterns = [
    path("auth/session/", SessionView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    # Signup privado: solo la administración puede registrar cuentas.
    path("auth/signup/", UsersView.as_view()),
    path("users/", UsersView.as_view()),
    path("universities/", UniversitiesView.as_view()),
    path("programs/", ProgramsView.as_view()),
]
