import getpass
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from accounts.models import Administrator, User


class Command(BaseCommand):
    help = "Crear la cuenta administradora inicial sin incluir contraseñas en código."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="volcan")

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"].strip().lower()
        if User.objects.filter(username=username).exists():
            raise CommandError("La cuenta ya existe; no se modificó su contraseña ni sus permisos.")
        password = os.environ.get("SIGMA_ADMIN_PASSWORD") or getpass.getpass("Contraseña inicial: ")
        if not password:
            raise CommandError("La contraseña no puede estar vacía.")
        user = User.objects.create_user(username=username, password=password, role=User.Role.ADMINISTRATOR, first_name=username)
        Administrator.objects.create(user=user, is_global=True)
        self.stdout.write(self.style.SUCCESS("Cuenta administradora global creada."))
