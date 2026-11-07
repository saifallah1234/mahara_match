from django.core.management.base import BaseCommand

from backend.apps.assistant.services.bootstrap import seed_assistant_rbac
from backend.apps.candidates.services.bootstrap import seed_candidates_rbac
from backend.apps.identity.services.bootstrap import seed_identity_rbac
from backend.apps.imports.services.bootstrap import seed_imports_rbac
from backend.apps.matching.services.bootstrap import seed_matching_rbac
from backend.apps.platform.services.bootstrap import seed_platform_rbac
from backend.apps.recruitment.services.bootstrap import seed_recruitment_rbac
from backend.apps.reporting.services.bootstrap import seed_reporting_rbac
from backend.apps.training.services.bootstrap import seed_training_rbac


class Command(BaseCommand):
    help = "Seed the application RBAC roles and permissions."

    def handle(self, *args: object, **options: object) -> None:
        seed_identity_rbac()
        seed_assistant_rbac()
        seed_candidates_rbac()
        seed_training_rbac()
        seed_recruitment_rbac()
        seed_matching_rbac()
        seed_imports_rbac()
        seed_platform_rbac()
        seed_reporting_rbac()
        self.stdout.write(self.style.SUCCESS("Application RBAC seeded."))
