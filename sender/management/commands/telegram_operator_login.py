"""Create or refresh the encrypted Telethon operator session in credentials."""

from __future__ import annotations

import asyncio
import getpass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models.network import NETWORK_SLUG_TELEGRAM, Credential, Network


def _resolve_telegram_credential(network: Network, label: str) -> Credential:
    """Pick credential by label, else default label, else first row."""
    qs = Credential.objects.filter(network=network)
    if label:
        cred = qs.filter(label=label).first()
        if cred is None:
            available = [
                row or "(default)" for row in qs.values_list("label", flat=True)
            ]
            raise CommandError(
                f"No Telegram credential with label {label!r}. "
                f"Available labels: {', '.join(available) or '(none)'}."
            )
        return cred

    cred = qs.filter(label="").first()
    if cred is not None:
        return cred

    cred = qs.order_by("pk").first()
    if cred is not None:
        return cred

    return Credential(network=network, label="")


class Command(BaseCommand):
    help = (
        "Authorize a Telegram user session for channel stories and store it in "
        "the default Telegram credential (operator_session)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--phone",
            help="Phone number in international format, e.g. +79001234567.",
        )
        parser.add_argument(
            "--credential-label",
            default="",
            help="Credential label to update (default credential uses empty label).",
        )

    def handle(self, *args, **options) -> None:
        try:
            network = Network.objects.get(slug=NETWORK_SLUG_TELEGRAM)
        except Network.DoesNotExist as exc:
            raise CommandError("Telegram network is not configured.") from exc

        label = (options.get("credential_label") or "").strip()
        cred = _resolve_telegram_credential(network, label)
        if label == "" and cred.pk and cred.label:
            self.stdout.write(
                self.style.WARNING(
                    f"Using credential label {cred.label!r} "
                    "(no default-label credential found)."
                ),
            )

        secrets = cred.get_secrets_dict() if cred.pk else {}
        api_id = secrets.get("api_id") or getattr(settings, "TELEGRAM_API_ID", None)
        api_hash = secrets.get("api_hash") or getattr(
            settings,
            "TELEGRAM_API_HASH",
            "",
        )
        if not api_id or not api_hash:
            cred_ref = f"{network.slug}:{cred.label or 'default'}"
            raise CommandError(
                f"Set api_id and api_hash in credential {cred_ref} JSON or env "
                "(TELEGRAM_API_ID / TELEGRAM_API_HASH)."
            )

        phone = (options.get("phone") or "").strip()
        if not phone:
            phone = input("Telegram phone (+…): ").strip()
        if not phone:
            raise CommandError("Phone number is required.")

        session_string = asyncio.run(
            _authorize_session(int(api_id), str(api_hash), phone),
        )
        secrets["api_id"] = int(api_id)
        secrets["api_hash"] = str(api_hash)
        secrets["operator_session"] = session_string
        cred.set_secrets_dict(secrets)
        cred.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Saved operator_session on credential "
                f"{network.slug}:{label or 'default'}."
            ),
        )


async def _authorize_session(api_id: int, api_hash: str, phone: str) -> str:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    from telethon.sessions import StringSession

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input("Telegram login code: ").strip()
            try:
                await client.sign_in(phone=phone, code=code)
            except SessionPasswordNeededError:
                password = getpass.getpass("Telegram 2FA password: ")
                await client.sign_in(password=password)
        if client.session is None:
            raise CommandError("Telegram session was not initialized.")
        session = client.session.save()
        if not isinstance(session, str):
            raise CommandError("Unexpected Telethon session format.")
        return session
    finally:
        await client.disconnect()  # pyright: ignore[reportGeneralTypeIssues]
