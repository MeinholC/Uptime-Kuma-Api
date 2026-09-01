from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from uptime_kuma_api import MonitorType, UptimeKumaException

from app.config import settings
from app.kuma_client import KumaApiError, kuma_session
from app.schemas import DomainCreate, DomainOut, DomainUpdate, Message
from app.security import require_api_key

router = APIRouter(prefix="/domains", tags=["domains"], dependencies=[Depends(require_api_key)])


def _build_url(domain: str, scheme: str) -> str:
    return f"{scheme}://{domain}"


def _domain_from_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed.netloc or parsed.path


def _to_domain_out(monitor: dict) -> DomainOut:
    return DomainOut(
        id=monitor["id"],
        domain=_domain_from_url(monitor.get("url")),
        name=monitor.get("name") or "",
        url=monitor.get("url") or "",
        active=bool(monitor.get("active", True)),
        interval=monitor.get("interval", settings.default_interval),
        retry_interval=monitor.get("retryInterval", settings.default_retry_interval),
        max_retries=monitor.get("maxretries", settings.default_max_retries),
        resend_interval=monitor.get("resendInterval", 0),
        upside_down=bool(monitor.get("upsideDown", False)),
        ignore_tls=bool(monitor.get("ignoreTls", False)),
        accepted_statuscodes=monitor.get("accepted_statuscodes") or ["200-299"],
        notification_ids=list(monitor.get("notificationIDList") or []),
    )


def _is_domain_monitor(monitor: dict) -> bool:
    monitor_type = monitor.get("type")
    return monitor_type == MonitorType.HTTP or monitor_type == MonitorType.HTTP.value


def _get_domain_monitor_or_404(api, monitor_id: int) -> dict:
    try:
        monitor = api.get_monitor(monitor_id)
    except UptimeKumaException as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No domain monitor with id {monitor_id}.") from exc
    if not _is_domain_monitor(monitor):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No domain monitor with id {monitor_id}.")
    return monitor


@router.get("", response_model=list[DomainOut])
def list_domains():
    """List all domains currently monitored (HTTP(s) monitors)."""
    try:
        with kuma_session() as api:
            monitors = api.get_monitors()
    except KumaApiError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    return [_to_domain_out(m) for m in monitors if _is_domain_monitor(m)]


@router.get("/{monitor_id}", response_model=DomainOut)
def get_domain(monitor_id: int):
    """Get a single monitored domain by its Uptime Kuma monitor id."""
    try:
        with kuma_session() as api:
            monitor = _get_domain_monitor_or_404(api, monitor_id)
    except KumaApiError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    return _to_domain_out(monitor)


@router.post("", response_model=DomainOut, status_code=status.HTTP_201_CREATED)
def create_domain(payload: DomainCreate):
    """Add a new domain to be monitored."""
    url = _build_url(payload.domain, payload.scheme)
    try:
        with kuma_session() as api:
            result = api.add_monitor(
                type=MonitorType.HTTP,
                name=payload.name or payload.domain,
                url=url,
                interval=payload.interval,
                retryInterval=payload.retry_interval,
                maxretries=payload.max_retries,
                resendInterval=payload.resend_interval,
                upsideDown=payload.upside_down,
                ignoreTls=payload.ignore_tls,
                accepted_statuscodes=payload.accepted_statuscodes,
                notificationIDList=payload.notification_ids,
            )
            monitor_id = result["monitorID"]
            if not payload.active:
                api.pause_monitor(monitor_id)
            monitor = api.get_monitor(monitor_id)
    except KumaApiError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    return _to_domain_out(monitor)


@router.put("/{monitor_id}", response_model=DomainOut)
def update_domain(monitor_id: int, payload: DomainUpdate):
    """Update fields of an existing monitored domain. Only provided fields are changed."""
    updates = payload.model_dump(exclude_unset=True, exclude={"active", "domain", "scheme"})

    field_map = {
        "retry_interval": "retryInterval",
        "max_retries": "maxretries",
        "resend_interval": "resendInterval",
        "upside_down": "upsideDown",
        "ignore_tls": "ignoreTls",
        "notification_ids": "notificationIDList",
    }
    kuma_updates = {field_map.get(k, k): v for k, v in updates.items()}

    try:
        with kuma_session() as api:
            existing = _get_domain_monitor_or_404(api, monitor_id)

            if payload.domain is not None or payload.scheme is not None:
                current_domain = _domain_from_url(existing.get("url"))
                new_domain = payload.domain if payload.domain is not None else current_domain
                new_scheme = payload.scheme or urlparse(existing.get("url") or "").scheme or settings.default_scheme
                kuma_updates["url"] = _build_url(new_domain, new_scheme)

            if kuma_updates:
                api.edit_monitor(monitor_id, **kuma_updates)

            if payload.active is not None:
                if payload.active:
                    api.resume_monitor(monitor_id)
                else:
                    api.pause_monitor(monitor_id)

            monitor = api.get_monitor(monitor_id)
    except KumaApiError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    return _to_domain_out(monitor)


@router.delete("/{monitor_id}", response_model=Message)
def delete_domain(monitor_id: int):
    """Stop monitoring a domain and remove it from Uptime Kuma."""
    try:
        with kuma_session() as api:
            _get_domain_monitor_or_404(api, monitor_id)
            api.delete_monitor(monitor_id)
    except KumaApiError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    return Message(message=f"Domain monitor {monitor_id} deleted.")
