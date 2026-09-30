import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ajaa migraatiot ja asettaa pääkäyttäjän ADMIN_USERNAME- ja ADMIN_PASSWORD-muuttujista."

    def handle(self, *args, **options):
        call_command("migrate", interactive=False)

        username = os.environ.get("ADMIN_USERNAME", "").strip()
        password = os.environ.get("ADMIN_PASSWORD", "").strip()
        if not username or not password:
            self.stdout.write("ADMIN_USERNAME tai ADMIN_PASSWORD puuttuu, käyttäjää ei päivitetty.")
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        action = "luotu" if created else "päivitetty"
        self.stdout.write(self.style.SUCCESS(f"Käyttäjä {username} {action}."))
