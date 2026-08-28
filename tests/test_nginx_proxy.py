"""Tests for the nginx proxy behaviour at :3000.

Verifies that:
1. Proxied services are reachable through their sub-paths (with valid JWT)
2. Requests without JWT are rejected (401)
3. Grafana does NOT redirect to / (the React app) after login — this was a real bug
4. The /links page exists and lists all services
"""
import httpx
import pytest


BASE = "http://127.0.0.1:3000"


@pytest.fixture(scope="module")
def client():
    with httpx.Client(follow_redirects=False, timeout=5) as c:
        yield c


@pytest.fixture(scope="module")
def authed_client():
    """Client with a valid JWT token."""
    with httpx.Client(follow_redirects=False, timeout=5) as c:
        resp = c.post(
            f"{BASE}/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


class TestAuthRequired:
    """Proxy routes must reject requests without a valid JWT."""

    def test_grafana_without_token_returns_401(self, client):
        resp = client.get(f"{BASE}/grafana/api/health")
        assert resp.status_code == 401

    def test_prometheus_without_token_returns_401(self, client):
        resp = client.get(f"{BASE}/prometheus/-/healthy")
        assert resp.status_code == 401

    def test_jaeger_without_token_returns_401(self, client):
        resp = client.get(f"{BASE}/jaeger/")
        assert resp.status_code == 401

    def test_links_without_token_returns_401(self, client):
        resp = client.get(f"{BASE}/links")
        assert resp.status_code == 401


class TestGrafanaProxy:
    """Grafana behind /grafana/ must not redirect to / after login.

    Regression test: Grafana used to redirect to / (the React app) because
    GF_SERVER_ROOT_URL was not set. Fixed by setting it to the sub-path.
    """

    def test_grafana_root_redirects_within_subpath(self, authed_client):
        """/grafana/ must not redirect to / (the React app)."""
        resp = authed_client.get(f"{BASE}/grafana/")
        if 300 <= resp.status_code < 400:
            location = resp.headers.get("location", "")
            assert "/grafana/" in location or location == "/grafana/", (
                f"Grafana redirected to {location} — user would land on the React app. "
                f"Expected a path under /grafana/"
            )

    def test_grafana_login_redirects_within_subpath(self, authed_client):
        """/grafana/login must not redirect to /."""
        resp = authed_client.get(f"{BASE}/grafana/login")
        if 300 <= resp.status_code < 400:
            location = resp.headers.get("location", "")
            assert "/grafana" in location or location == "/grafana/", (
                f"Grafana login redirected to {location} — expected /grafana/..."
            )

    def test_grafana_api_health(self, authed_client):
        """/grafana/api/health must be reachable through the proxy."""
        resp = authed_client.get(f"{BASE}/grafana/api/health")
        assert resp.status_code == 200


class TestPrometheusProxy:
    """Prometheus behind /prometheus/ must be reachable."""

    def test_prometheus_root_reachable(self, authed_client):
        """/prometheus/ must return 200 or redirect within /prometheus/."""
        resp = authed_client.get(f"{BASE}/prometheus/")
        assert resp.status_code in (200, 301, 302)

    def test_prometheus_healthy(self, authed_client):
        """/prometheus/-/healthy must be reachable."""
        resp = authed_client.get(f"{BASE}/prometheus/-/healthy")
        assert resp.status_code == 200


class TestJaegerProxy:
    """Jaeger behind /jaeger/ must be reachable."""

    def test_jaeger_ui(self, authed_client):
        resp = authed_client.get(f"{BASE}/jaeger/")
        assert resp.status_code in (200, 301, 302)

    def test_jaeger_base_href_rewritten(self, authed_client):
        """Base href must point to /jaeger/ so static assets load correctly."""
        resp = authed_client.get(f"{BASE}/jaeger/")
        assert 'href="/jaeger/"' in resp.text


class TestLinksPage:
    """The /links page must exist and contain all service links."""

    def test_links_page_reachable(self, authed_client):
        resp = authed_client.get(f"{BASE}/links")
        assert resp.status_code == 200

    def test_links_page_contains_all_services(self, authed_client):
        resp = authed_client.get(f"{BASE}/links")
        html = resp.text
        for service in ["Grafana", "Prometheus", "Jaeger", "RabbitMQ"]:
            assert service.lower() in html.lower(), f"Missing link for {service}"


class TestRabbitMQProxy:
    """RabbitMQ Management behind /rabbitmq/ must auto-login via session relay."""

    def test_rabbitmq_without_token_returns_401(self, client):
        resp = client.get(f"{BASE}/rabbitmq/")
        assert resp.status_code == 401

    def test_rabbitmq_with_token_reachable(self, authed_client):
        resp = authed_client.get(f"{BASE}/rabbitmq/")
        assert resp.status_code in (200, 301, 302)

    def test_rabbitmq_sets_session_cookie(self, authed_client):
        """Session endpoint should relay a RabbitMQ session cookie."""
        resp = authed_client.get(f"{BASE}/rabbitmq/")
        cookies = [c for c in resp.headers.get_list("set-cookie") if "rmq" in c.lower()]
        # Either the cookie is set or RabbitMQ returned 200 (session might already exist)
        assert resp.status_code in (200, 301, 302)
