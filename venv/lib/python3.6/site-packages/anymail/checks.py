from django.conf import settings
from django.core import checks


def check_deprecated_settings(app_configs, **kwargs):
    errors = []

    anymail_settings = getattr(settings, "ANYMAIL", {})

    # anymail.W001: reserved [was deprecation warning that became anymail.E001]

    # anymail.E001: rename WEBHOOK_AUTHORIZATION to WEBHOOK_SECRET
    if "WEBHOOK_AUTHORIZATION" in anymail_settings:
        errors.append(checks.Error(
            "The ANYMAIL setting 'WEBHOOK_AUTHORIZATION' has been renamed 'WEBHOOK_SECRET' to improve security.",
            hint="You must update your settings.py.",
            id="anymail.E001",
        ))
    if hasattr(settings, "ANYMAIL_WEBHOOK_AUTHORIZATION"):
        errors.append(checks.Error(
            "The ANYMAIL_WEBHOOK_AUTHORIZATION setting has been renamed ANYMAIL_WEBHOOK_SECRET to improve security.",
            hint="You must update your settings.py.",
            id="anymail.E001",
        ))

    return errors
