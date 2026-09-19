from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import AcademicProgram, University, User
from .permissions import IsAdministrator, accessible_universities, administrator_for
from .serializers import ProgramSerializer, UniversitySerializer, UserCreateSerializer, user_data
from .services import create_account


@method_decorator(never_cache, name="dispatch")
class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"user": user_data(request.user) if request.user.is_authenticated else None, "csrfToken": get_token(request)})


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, username=serializer.validated_data["username"].strip().lower(), password=serializer.validated_data["password"])
        if user is None:
            return Response({"detail": "Usuario o contraseña incorrectos."}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response({"user": user_data(user), "csrfToken": get_token(request)})


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"detail": "Sesión cerrada."})


class UniversitiesView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        return Response(UniversitySerializer(accessible_universities(request.user), many=True).data)

    def post(self, request):
        if not administrator_for(request.user).is_global:
            raise PermissionDenied("Solo la administración global puede afiliar universidades.")
        serializer = UniversitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise ValidationError({"detail": "El nombre o dominio ya está registrado."})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProgramsView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        programs = AcademicProgram.objects.filter(university__in=accessible_universities(request.user))
        return Response(ProgramSerializer(programs, many=True).data)

    def post(self, request):
        serializer = ProgramSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise ValidationError({"name": "Este programa ya está registrado."})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(never_cache, name="dispatch")
class UsersView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        universities = accessible_universities(request.user)
        users = User.objects.filter(Q(teacher__university__in=universities) | Q(student__academic_program__university__in=universities)).select_related("teacher__university", "student__academic_program__university").order_by("-id")
        return Response([user_data(user) for user in users])

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = create_account(request.user, serializer.validated_data)
        return Response(user_data(user), status=status.HTTP_201_CREATED)
