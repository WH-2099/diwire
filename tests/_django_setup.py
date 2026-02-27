from __future__ import annotations

import secrets

import django
from django.apps import apps
from django.conf import settings


def ensure_django_setup() -> None:
    if not settings.configured:
        settings.configure(
            ALLOWED_HOSTS=["*"],
            INSTALLED_APPS=[],
            MIDDLEWARE=[],
            SECRET_KEY=secrets.token_hex(16),
        )

    if not apps.ready:
        django.setup()
