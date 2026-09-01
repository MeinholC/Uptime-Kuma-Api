from contextlib import contextmanager
from typing import Iterator

from uptime_kuma_api import UptimeKumaApi, UptimeKumaException

from app.config import settings


class KumaApiError(Exception):
    """Raised when talking to Uptime Kuma fails: connection, login, or a rejected operation."""


@contextmanager
def kuma_session() -> Iterator[UptimeKumaApi]:
    """Open a short-lived Socket.IO session against the configured Uptime Kuma instance.

    A fresh connection is used per request instead of a shared long-lived one so that
    a dropped Uptime Kuma connection never leaves this service in a broken state.
    """
    try:
        api = UptimeKumaApi(settings.uptime_kuma_url, timeout=settings.uptime_kuma_timeout)
    except Exception as exc:  # socketio raises plain Exception/ConnectionError subclasses
        raise KumaApiError(f"Could not connect to Uptime Kuma at {settings.uptime_kuma_url}: {exc}") from exc

    try:
        api.login(settings.uptime_kuma_username, settings.uptime_kuma_password)
        yield api
    except UptimeKumaException as exc:
        raise KumaApiError(str(exc)) from exc
    finally:
        api.disconnect()
