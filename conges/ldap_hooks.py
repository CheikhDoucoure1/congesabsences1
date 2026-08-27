"""Hooks wired into django-auth-ldap's signals (see apps.py).

Only imported/connected when LDAP auth is actually enabled
(settings.AUTH_LDAP_ENABLED) — see conges_absences/settings.py.
"""
from django.dispatch import receiver
from django_auth_ldap.backend import populate_user


@receiver(populate_user)
def bloquer_mot_de_passe_local(sender, user, ldap_user, **kwargs):
    """AD is the sole source of truth for this account's password: make
    sure no locally-set password (leftover, or set by mistake) can ever be
    used to log in through ModelBackend instead of LDAP.

    Runs on every successful LDAP login (new or existing account), so if an
    admin temporarily sets a local password for this user during an AD
    outage (a manual break-glass step — there is no self-service flow for
    it today), it stays valid only until the user next authenticates via
    LDAP again, at which point AD is authoritative once more.
    """
    user.set_unusable_password()
