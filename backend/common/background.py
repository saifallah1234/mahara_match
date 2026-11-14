# Placement: backend/common/background.py
"""Start a long task (`python -m <module> ...`) in its own process and return at once.

Used when work takes minutes (browser scraping, CV analysis by an LLM) and must not
run inside an HTTP request. The child gets the same settings module and environment,
outlives a runserver reload, and writes its output to `log_file`.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from django.conf import settings


def logs_dir(*parts: str) -> Path:
    return Path(settings.BASE_DIR, "logs", *parts)


def start_module(module: str, arguments: list[str], log_file: Path) -> None:
    """Raises OSError when the process cannot be started."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    environment = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": settings.SETTINGS_MODULE,
        "PYTHONIOENCODING": "utf-8",
    }
    options: dict[str, Any] = {}
    if os.name == "nt":
        # Own process group, no console window; it outlives a runserver reload.
        options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    else:
        options["start_new_session"] = True
    with log_file.open("ab") as log:
        subprocess.Popen(  # noqa: S603 - fixed module, arguments are ids
            [sys.executable, "-m", module, *arguments],
            cwd=settings.BASE_DIR,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            **options,
        )
