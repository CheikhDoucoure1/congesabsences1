"""Email notifications — a deliberately small subset of the in-app
Notification events (see conges/views.py's _notifier_* functions).

Only two kinds of moments send an email:
  - "Something needs your action" (a request is waiting for you to
    approve/reject, at whichever stage).
  - "Here's the final decision on your own request" (approved or
    rejected — not the intermediate validee_manager/validee progress
    updates, those stay in-app only).

Everything else (a new request just submitted notifying RH ahead of time,
a supérieur being changed, a congé supplémentaire credit, ...) stays as an
in-app notification only, to keep inboxes from filling up with every step
of every request for every one of ~80 employees.

Sending never raises — a broken/unconfigured mailbox must never block the
actual leave-request workflow. Failures are logged instead.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _url_absolue(lien_relatif):
    if not lien_relatif:
        return ''
    return settings.SITE_URL + lien_relatif


def envoyer_email_notification(destinataire, sujet, message, lien_relatif=None):
    """Best-effort email to `destinataire` (an Employe). No-op if they have
    no email on file; never raises on a send failure."""
    if not destinataire.email:
        return
    corps = message
    lien = _url_absolue(lien_relatif)
    if lien:
        corps += f"\n\n{lien}"
    try:
        send_mail(
            subject=f"[Congés PETROSEN] {sujet}",
            message=corps,
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[destinataire.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Échec d'envoi d'email de notification à %s", destinataire.email)
