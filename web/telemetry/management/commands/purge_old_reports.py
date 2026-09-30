from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from telemetry.models import Report


class Command(BaseCommand):
    help = "Poistaa yli 90 päivää vanhat tuntiraportit."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=90)
        deleted, _detail = Report.objects.filter(period_start__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Poistettu {deleted} riviä."))
