import re

from rest_framework import serializers
from .models import AcademicProgram, University, User
from .permissions import accessible_universities, administrator_for


class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ["id", "name", "email_domain"]

    def validate_name(self, value):
        value = " ".join(value.split())
        if University.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Esta universidad ya está afiliada.")
        return value

    def validate_email_domain(self, value):
        value = value.strip().lower()
        try:
            value = value.encode("idna").decode("ascii")
        except UnicodeError:
            raise serializers.ValidationError("Dominio no válido.")
        labels = value.split(".")
        if len(value) > 253 or len(labels) < 2 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels) or not re.fullmatch(r"[a-z]{2,63}", labels[-1]):
            raise serializers.ValidationError("Escribe solo el dominio, por ejemplo ufps.edu.co; sin @ ni https://.")
        if University.objects.filter(email_domain=value).exists():
            raise serializers.ValidationError("Este dominio ya está registrado.")
        return value


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicProgram
        fields = ["id", "name", "university"]

    def validate(self, attrs):
        if not accessible_universities(self.context["request"].user).filter(pk=attrs["university"].pk).exists():
            raise serializers.ValidationError({"university": "Universidad no autorizada."})
        attrs["name"] = " ".join(attrs["name"].split())
        if AcademicProgram.objects.filter(university=attrs["university"], name__iexact=attrs["name"]).exists():
            raise serializers.ValidationError({"name": "Este programa ya existe en la universidad."})
        return attrs


class UserCreateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[User.Role.TEACHER, User.Role.STUDENT])
    first_name = serializers.CharField(max_length=150)
    first_surname = serializers.CharField(max_length=100)
    second_surname = serializers.CharField(max_length=100)
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all())
    academic_program = serializers.PrimaryKeyRelatedField(queryset=AcademicProgram.objects.all(), required=False, allow_null=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=128, trim_whitespace=False)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({"detail": "El formulario contiene campos no permitidos."})
        return super().to_internal_value(data)

    def validate(self, attrs):
        for key in ["first_name", "first_surname", "second_surname"]:
            attrs[key] = " ".join(attrs[key].split())
        if len(f'{attrs["first_surname"]} {attrs["second_surname"]}') > 150:
            raise serializers.ValidationError({"last_name": "Los apellidos son demasiado largos."})
        return attrs


def user_data(user):
    result = {"id": user.pk, "username": user.username, "email": user.email, "first_name": user.first_name,
              "first_surname": user.first_surname, "second_surname": user.second_surname, "role": user.role,
              "code": None, "university": None, "academic_program": None, "is_global_admin": False}
    if user.role == User.Role.STUDENT:
        profile = user.student
        result.update(code=profile.pk, university=profile.university.name, academic_program=profile.academic_program.name)
    elif user.role == User.Role.TEACHER:
        profile = user.teacher
        result.update(code=profile.pk, university=profile.university.name)
    else:
        administrator = administrator_for(user)
        result["is_global_admin"] = bool(administrator and administrator.is_global)
    return result
