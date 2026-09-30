import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ajaa migraatiot ja luo pääkäyttäjän, jos sitä ei vielä ole."

    def handle(self, *args, **options):
        call_command("migrate", interactive=False)

        username = os.environ.get("ADMIN_USERNAME", "").strip()
        password = os.environ.get("ADMIN_PASSWORD", "")
        if not username or not password:
            self.stdout.write("ADMIN_USERNAME tai ADMIN_PASSWORD puuttuu, käyttäjää ei luotu.")
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Käyttäjä {username} on jo olemassa.")
            return
        User.objects.create_superuser(username=username, email="", password=password)
        self.stdout.write(self.style.SUCCESS(f"Käyttäjä {username} luotu."))
