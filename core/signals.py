"""Security-related Django signal handlers."""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.mail import send_mail
from django.dispatch import receiver

log = logging.getLogger(__name__)


@receiver(user_logged_in, dispatch_uid="core_rotate_session_on_login")
def rotate_session_on_login(sender, request, user, **kwargs):
    """Issue a new session key after successful authentication."""
    if request is not None and hasattr(request, "session"):
        request.session.cycle_key()


def _send_lockout_email(subject: str, body: str) -> None:
    admin_email = getattr(settings, "ADMIN_EMAIL", "") or ""
    if not admin_email:
        log.warning("ADMIN_EMAIL is not set; skipping lockout notification email.")
        return
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[admin_email],
        fail_silently=False,
    )


def handle_user_locked_out(sender, request, username, ip_address, **kwargs):
    """Notify admin when django-axes locks an account."""
    subject = f"[shiftedblog] Account lockout: {username}"
    body = (
        f"Account lockout detected.\n\n"
        f"Username: {username}\n"
        f"IP address: {ip_address}\n"
        f"Path: {getattr(request, 'path', '')}\n"
    )
    log.warning("Account lockout for %s from %s", username, ip_address)
    try:
        _send_lockout_email(subject, body)
    except Exception:
        log.exception("Failed to send lockout notification email for %s", username)


def connect_security_signals() -> None:
    """Register handlers that are not auto-discovered by Django."""
    from axes.signals import user_locked_out

    user_locked_out.connect(handle_user_locked_out, dispatch_uid="core_lockout_email")
