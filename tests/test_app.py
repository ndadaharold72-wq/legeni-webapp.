import runpy
import sys
import types

import pytest

from app import MemoryCounter, RedisCounter, build_counter, create_app


class DownCounter(MemoryCounter):
    """Simule un Redis injoignable."""

    def ping(self):
        return False


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("APP_ENV", "test")
    app = create_app(counter=MemoryCounter())
    return app.test_client()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_ready_with_memory_counter(client):
    assert client.get("/ready").status_code == 200


def test_ready_returns_503_when_redis_down():
    client = create_app(counter=DownCounter()).test_client()
    assert client.get("/ready").status_code == 503


def test_index_shows_version_and_env(client):
    body = client.get("/").get_data(as_text=True)
    assert "Version 1.2.3" in body
    assert "test" in body


def test_visits_are_counted(client):
    client.get("/")
    body = client.get("/").get_data(as_text=True)
    assert "<b>2</b>" in body


def test_api_info(client):
    data = client.get("/api/info").get_json()
    assert data["app"] == "legeni-webapp"
    assert data["version"] == "1.2.3"
    assert data["hostname"]


def test_build_counter_uses_memory_when_redis_host_missing(monkeypatch):
    monkeypatch.delenv("REDIS_HOST", raising=False)
    assert isinstance(build_counter(), MemoryCounter)


def test_build_counter_uses_redis_from_environment(monkeypatch):
    class FakeRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def incr(self, _key):
            return 7

        def ping(self):
            return True

    monkeypatch.setenv("REDIS_HOST", "redis.test")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_PASSWORD", "secret")
    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(Redis=FakeRedisClient))

    counter = build_counter()

    assert isinstance(counter, RedisCounter)
    assert counter.client.kwargs == {
        "host": "redis.test", "port": 6380, "password": "secret", "socket_timeout": 2
    }
    assert counter.incr() == 7
    assert counter.ping() is True


def test_build_counter_uses_redis_defaults_and_ignores_empty_password(monkeypatch):
    class FakeRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setenv("REDIS_HOST", "redis.test")
    monkeypatch.delenv("REDIS_PORT", raising=False)
    monkeypatch.setenv("REDIS_PASSWORD", "")
    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(Redis=FakeRedisClient))

    counter = build_counter()

    assert counter.client.kwargs == {
        "host": "redis.test", "port": 6379, "password": None, "socket_timeout": 2
    }


def test_redis_counter_ping_returns_false_on_connection_error(monkeypatch):
    class BrokenRedisClient:
        def __init__(self, **_kwargs):
            pass

        def ping(self):
            raise OSError("connection refused")

    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(Redis=BrokenRedisClient))
    assert RedisCounter("redis.test", 6379).ping() is False


def test_index_uses_custom_banner_color(client, monkeypatch):
    monkeypatch.setenv("APP_COLOR", "#d1242f")
    body = client.get("/").get_data(as_text=True)
    assert "background: #d1242f" in body


def test_module_entrypoint_starts_flask(monkeypatch):
    from flask import Flask

    started = []
    monkeypatch.setattr(Flask, "run", lambda self, **kwargs: started.append(kwargs))
    runpy.run_module("app", run_name="__main__")
    assert started == [{"host": "0.0.0.0", "port": 5000}]


def test_module_entrypoint_uses_port_environment(monkeypatch):
    from flask import Flask

    started = []
    monkeypatch.setenv("PORT", "5050")
    monkeypatch.setattr(Flask, "run", lambda self, **kwargs: started.append(kwargs))
    runpy.run_module("app", run_name="__main__")
    assert started == [{"host": "0.0.0.0", "port": 5050}]


def test_api_info_uses_default_version_and_environment(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    data = create_app(counter=MemoryCounter()).test_client().get("/api/info").get_json()
    assert data["version"] == "dev"
    assert data["env"] == "dev"
