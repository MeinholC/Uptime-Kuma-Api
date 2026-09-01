from contextlib import contextmanager

import pytest
from uptime_kuma_api import MonitorType

from app.routers import domains as domains_module


class FakeKumaApi:
    """In-memory stand-in for uptime_kuma_api.UptimeKumaApi used in tests."""

    def __init__(self):
        self._next_id = 1
        self.monitors: dict[int, dict] = {}

    def get_monitors(self):
        return list(self.monitors.values())

    def get_monitor(self, id_):
        if id_ not in self.monitors:
            from uptime_kuma_api import UptimeKumaException

            raise UptimeKumaException("monitor not found")
        return self.monitors[id_]

    def add_monitor(self, **kwargs):
        monitor_id = self._next_id
        self._next_id += 1
        monitor = {
            "id": monitor_id,
            "type": kwargs.get("type", MonitorType.HTTP),
            "name": kwargs.get("name"),
            "url": kwargs.get("url"),
            "active": True,
            "interval": kwargs.get("interval", 60),
            "retryInterval": kwargs.get("retryInterval", 60),
            "maxretries": kwargs.get("maxretries", 0),
            "resendInterval": kwargs.get("resendInterval", 0),
            "upsideDown": kwargs.get("upsideDown", False),
            "ignoreTls": kwargs.get("ignoreTls", False),
            "accepted_statuscodes": kwargs.get("accepted_statuscodes", ["200-299"]),
            "notificationIDList": kwargs.get("notificationIDList", []),
        }
        self.monitors[monitor_id] = monitor
        return {"monitorID": monitor_id, "msg": "Added Successfully."}

    def edit_monitor(self, id_, **kwargs):
        monitor = self.get_monitor(id_)
        monitor.update(kwargs)
        return {"monitorID": id_, "msg": "Saved."}

    def delete_monitor(self, id_):
        self.monitors.pop(id_, None)
        return {"msg": "Deleted Successfully."}

    def pause_monitor(self, id_):
        self.monitors[id_]["active"] = False
        return {"msg": "Paused Successfully."}

    def resume_monitor(self, id_):
        self.monitors[id_]["active"] = True
        return {"msg": "Resumed Successfully."}


@pytest.fixture
def fake_api(monkeypatch):
    api = FakeKumaApi()

    @contextmanager
    def fake_kuma_session():
        yield api

    monkeypatch.setattr(domains_module, "kuma_session", fake_kuma_session)
    return api


def test_requires_api_key(client, fake_api):
    response = client.get("/domains")
    assert response.status_code == 401


def test_rejects_wrong_api_key(client, fake_api):
    response = client.get("/domains", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_create_and_list_domain(client, fake_api, auth_headers):
    response = client.post("/domains", json={"domain": "example.com"}, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["domain"] == "example.com"
    assert body["url"] == "https://example.com"
    assert body["active"] is True

    response = client.get("/domains", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["domain"] == "example.com"


def test_create_domain_inactive(client, fake_api, auth_headers):
    response = client.post(
        "/domains",
        json={"domain": "paused.example.com", "active": False},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["active"] is False


def test_get_domain(client, fake_api, auth_headers):
    created = client.post("/domains", json={"domain": "example.com"}, headers=auth_headers).json()

    response = client.get(f"/domains/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["domain"] == "example.com"


def test_get_unknown_domain_returns_404(client, fake_api, auth_headers):
    response = client.get("/domains/999", headers=auth_headers)
    assert response.status_code == 404


def test_update_domain(client, fake_api, auth_headers):
    created = client.post("/domains", json={"domain": "old.example.com"}, headers=auth_headers).json()

    response = client.put(
        f"/domains/{created['id']}",
        json={"domain": "new.example.com", "interval": 120, "active": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["domain"] == "new.example.com"
    assert body["url"] == "https://new.example.com"
    assert body["interval"] == 120
    assert body["active"] is False


def test_delete_domain(client, fake_api, auth_headers):
    created = client.post("/domains", json={"domain": "example.com"}, headers=auth_headers).json()

    response = client.delete(f"/domains/{created['id']}", headers=auth_headers)
    assert response.status_code == 200

    response = client.get(f"/domains/{created['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_health_endpoint_needs_no_api_key(client, fake_api):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
