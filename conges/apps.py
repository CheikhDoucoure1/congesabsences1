from django.apps import AppConfig
from django.conf import settings


class CongesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'conges'

    def ready(self):
        if getattr(settings, 'AUTH_LDAP_ENABLED', False):
            from . import ldap_hooks  # noqa: F401 — connects the populate_user signal
