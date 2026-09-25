from django.core.management.base import BaseCommand

from backend.apps.identity.services.bootstrap import seed_identity_rbac
from backend.apps.training.services.bootstrap import seed_training_rbac


class Command(BaseCommand):
    help = "Seed the identity and training RBAC roles and permissions."

    def handle(self, *args: object, **options: object) -> None:
        seed_identity_rbac()
        seed_training_rbac()
        self.stdout.write(self.style.SUCCESS("Identity and training RBAC seeded."))
