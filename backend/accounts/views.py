from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
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

from .academic_service import cancel_enrollment, change_group_status, promote_waitlist, request_enrollment
from .models import AcademicProgram, Course, Enrollment, Group, GroupSchedule, Notification, Teacher, University, User
from .permissions import IsAdministrator, IsStudent, accessible_universities, administrator_for
from .serializers import CourseCreateSerializer, GroupCreateSerializer, GroupUpdateSerializer, ProgramSerializer, UniversitySerializer, UserCreateSerializer, course_data, user_data
from .services import create_account
from .password_service import change_password
from .serializers import PasswordChangeSerializer, session_user_data


@method_decorator(never_cache, name="dispatch")
class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"user": session_user_data(request.user) if request.user.is_authenticated else None, "csrfToken": get_token(request)})


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
        return Response({"user": session_user_data(user), "csrfToken": get_token(request)})


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"detail": "Sesión cerrada."})


@method_decorator(never_cache, name="dispatch")
class PasswordChangeView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_change"

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = change_password(request.user, **serializer.validated_data)
        update_session_auth_hash(request, user)
        return Response({"user": user_data(user), "csrfToken": get_token(request), "detail": "Contraseña actualizada."})


@method_decorator(never_cache, name="dispatch")
class ProfileView(APIView):
    def get(self, request):
        # Nunca aceptar IDs del cliente para seleccionar otro perfil.
        return Response(user_data(request.user))


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


class TeachersView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        teachers = Teacher.objects.filter(university__in=accessible_universities(request.user)).select_related("user", "university")
        return Response([
            {
                "id": teacher.pk,
                "name": teacher.user.get_full_name(),
                "email": teacher.user.email,
                "university": teacher.university_id,
            }
            for teacher in teachers
        ])


class CoursesView(APIView):
    def get(self, request):
        courses = Course.objects.select_related("curriculum__academic_program__university").prefetch_related("prerequisites", "groups__teacher__user")
        student = None
        if request.user.role == User.Role.ADMINISTRATOR:
            courses = courses.filter(curriculum__academic_program__university__in=accessible_universities(request.user))
        elif request.user.role == User.Role.STUDENT and hasattr(request.user, "student"):
            student = request.user.student
            courses = courses.filter(curriculum__academic_program=student.academic_program)
        elif request.user.role == User.Role.TEACHER and hasattr(request.user, "teacher"):
            courses = courses.filter(groups__teacher=request.user.teacher)
        else:
            courses = courses.none()
        return Response([course_data(course, student=student) for course in courses.distinct()])

    def post(self, request):
        if administrator_for(request.user) is None:
            raise PermissionDenied("Solo la administración puede crear cursos.")
        serializer = CourseCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                teacher = Teacher.objects.select_for_update().get(pk=serializer.validated_data["teacher"].pk)
                serializer.validated_data["teacher"] = teacher
                serializer.validate(serializer.validated_data)
                course = serializer.save()
        except IntegrityError:
            raise ValidationError({"detail": "La materia ya está registrada en este pensum."})
        course = Course.objects.select_related("curriculum__academic_program__university").prefetch_related("prerequisites").get(pk=course.pk)
        return Response(course_data(course), status=status.HTTP_201_CREATED)


class CourseGroupsView(APIView):
    permission_classes = [IsAdministrator]

    def post(self, request, course_id):
        course = Course.objects.select_related("curriculum__academic_program__university").filter(pk=course_id).first()
        if course is None:
            return Response({"detail": "Materia no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        if not accessible_universities(request.user).filter(pk=course.curriculum.university.pk).exists():
            raise PermissionDenied("Materia fuera de tu alcance institucional.")
        serializer = GroupCreateSerializer(data=request.data, context={"course": course})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            locked_course = Course.objects.select_for_update().select_related("curriculum__academic_program__university").get(pk=course.pk)
            teacher = Teacher.objects.select_for_update().get(pk=serializer.validated_data["teacher"].pk)
            serializer.validated_data["teacher"] = teacher
            serializer.context["course"] = locked_course
            serializer.validate(serializer.validated_data)
            serializer.save()
        course = Course.objects.select_related("curriculum__academic_program__university").prefetch_related("prerequisites").get(pk=course.pk)
        return Response(course_data(course), status=status.HTTP_201_CREATED)


class GroupStatusView(APIView):
    permission_classes = [IsAdministrator]

    def patch(self, request, group_id):
        group = Group.objects.filter(pk=group_id).select_related("course__curriculum__academic_program__university").first()
        if group is None:
            return Response({"detail": "Curso no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        university_id = group.course.curriculum.academic_program.university_id
        if not accessible_universities(request.user).filter(pk=university_id).exists():
            raise PermissionDenied("Curso fuera de tu alcance institucional.")
        changed = change_group_status(group.pk, request.data.get("status"))
        course = Course.objects.select_related("curriculum__academic_program__university").prefetch_related("prerequisites").get(pk=changed.course_id)
        return Response(course_data(course))


class GroupConfigurationView(APIView):
    permission_classes = [IsAdministrator]

    def patch(self, request, group_id):
        group = Group.objects.select_related("course__curriculum__academic_program__university").filter(pk=group_id).first()
        if group is None:
            return Response({"detail": "Grupo no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        if not accessible_universities(request.user).filter(pk=group.course.curriculum.university.pk).exists():
            raise PermissionDenied("Grupo fuera de tu alcance institucional.")
        serializer = GroupUpdateSerializer(group, data=request.data, context={"group": group})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            locked = Group.objects.select_for_update().select_related("course__curriculum__academic_program__university").get(pk=group.pk)
            teacher = Teacher.objects.select_for_update().get(pk=serializer.validated_data["teacher"].pk)
            serializer.validated_data["teacher"] = teacher
            serializer.instance = locked
            serializer.context["group"] = locked
            serializer.validate(serializer.validated_data)
            serializer.save()
            while locked.enrollments.filter(status=Enrollment.Status.CONFIRMED).count() < locked.capacity:
                if promote_waitlist(locked) is None:
                    break
        course = Course.objects.select_related("curriculum__academic_program__university").prefetch_related("prerequisites").get(pk=group.course_id)
        return Response(course_data(course))


class EnrollmentRequestView(APIView):
    permission_classes = [IsStudent]

    def post(self, request, group_id):
        if not Group.objects.filter(pk=group_id).exists():
            return Response({"detail": "Curso no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        enrollment = request_enrollment(request.user.student, group_id)
        message = "Matrícula confirmada." if enrollment.status == enrollment.Status.CONFIRMED else "Cupo lleno: ingresaste a la lista de espera."
        return Response({"id": enrollment.pk, "status": enrollment.status, "detail": message}, status=status.HTTP_201_CREATED)


class EnrollmentCancelView(APIView):
    permission_classes = [IsStudent]

    def delete(self, request, enrollment_id):
        enrollment, promoted, was_confirmed = cancel_enrollment(request.user.student, enrollment_id)
        detail = "Matrícula cancelada." if was_confirmed else "Salida de la lista de espera confirmada."
        return Response({"detail": detail, "promoted": promoted.pk if promoted else None})


class ScheduleView(APIView):
    def get(self, request):
        blocks = GroupSchedule.objects.select_related("group__course", "group__teacher__user")
        if request.user.role == User.Role.STUDENT and hasattr(request.user, "student"):
            blocks = blocks.filter(
                group__enrollments__student=request.user.student,
                group__enrollments__status=Enrollment.Status.CONFIRMED,
            ).exclude(group__status=Group.Status.FINISHED)
        elif request.user.role == User.Role.TEACHER and hasattr(request.user, "teacher"):
            blocks = blocks.filter(group__teacher=request.user.teacher).exclude(group__status=Group.Status.FINISHED)
        else:
            blocks = blocks.none()
        return Response([{
            "id": block.pk,
            "day_of_week": block.day_of_week,
            "day": block.get_day_of_week_display(),
            "start_time": block.start_time.strftime("%H:%M"),
            "end_time": block.end_time.strftime("%H:%M"),
            "course": block.group.course.name,
            "section": block.group.section,
            "group": block.group_id,
            "teacher": block.group.teacher.user.get_full_name(),
        } for block in blocks.distinct()])


class NotificationsView(APIView):
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        return Response([{
            "id": item.pk,
            "title": item.title,
            "message": item.message,
            "read": item.read,
            "created_at": item.created_at.isoformat(),
        } for item in notifications])


class NotificationReadView(APIView):
    def patch(self, request, notification_id):
        notification = Notification.objects.filter(pk=notification_id, user=request.user).first()
        if notification is None:
            return Response({"detail": "Notificación no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        notification.read = True
        notification.save(update_fields=["read"])
        return Response({"id": notification.pk, "read": True})


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
