"""Tests for the nginx proxy behaviour at :3000.

Verifies that:
1. Proxied services are reachable through their sub-paths
2. Grafana does NOT redirect to / (the React app) after login — this was a real bug
3. The /links page exists and lists all services
"""
import httpx
import pytest


BASE = "http://127.0.0.1:3000"


@pytest.fixture(scope="module")
def client():
    with httpx.Client(follow_redirects=False, timeout=5) as c:
        yield c


class TestGrafanaProxy:
    """Grafana behind /grafana/ must not redirect to / after login.

    Regression test: Grafana used to redirect to / (the React app) because
    GF_SERVER_ROOT_URL was not set. Fixed by setting it to the sub-path.
    """

    def test_grafana_root_redirects_within_subpath(self, client):
        """/grafana/ must not redirect to / (the React app)."""
        resp = client.get(f"{BASE}/grafana/")
        if 300 <= resp.status_code < 400:
            location = resp.headers.get("location", "")
            assert "/grafana/" in location or location == "/grafana/", (
                f"Grafana redirected to {location} — user would land on the React app. "
                f"Expected a path under /grafana/"
            )

    def test_grafana_login_redirects_within_subpath(self, client):
        """/grafana/login must not redirect to /."""
        resp = client.get(f"{BASE}/grafana/login")
        if 300 <= resp.status_code < 400:
            location = resp.headers.get("location", "")
            assert "/grafana" in location or location == "/grafana/", (
                f"Grafana login redirected to {location} — expected /grafana/..."
            )

    def test_grafana_api_health(self, client):
        """/grafana/api/health must be reachable through the proxy."""
        resp = client.get(f"{BASE}/grafana/api/health")
        assert resp.status_code == 200


class TestPrometheusProxy:
    """Prometheus behind /prometheus/ must be reachable."""

    def test_prometheus_root_reachable(self, client):
        """/prometheus/ must return 200 or redirect within /prometheus/."""
        resp = client.get(f"{BASE}/prometheus/")
        assert resp.status_code in (200, 301, 302)

    def test_prometheus_healthy(self, client):
        """/prometheus/-/healthy must be reachable."""
        resp = client.get(f"{BASE}/prometheus/-/healthy")
        assert resp.status_code == 200


class TestJaegerProxy:
    """Jaeger behind /jaeger/ must be reachable."""

    def test_jaeger_ui(self, client):
        resp = client.get(f"{BASE}/jaeger/")
        assert resp.status_code in (200, 301, 302)


class TestLinksPage:
    """The /links page must exist and contain all service links."""

    def test_links_page_reachable(self, client):
        resp = client.get(f"{BASE}/links")
        assert resp.status_code == 200

    def test_links_page_contains_all_services(self, client):
        resp = client.get(f"{BASE}/links")
        html = resp.text
        for service in ["Grafana", "Prometheus", "Jaeger", "RabbitMQ"]:
            assert service.lower() in html.lower(), f"Missing link for {service}"
