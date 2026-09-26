#!/usr/bin/env python
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    repository_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repository_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings.development")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
