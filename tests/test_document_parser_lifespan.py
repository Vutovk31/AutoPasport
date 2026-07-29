from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app import main as main_module
from app.document_parser_composition import DocumentParserConfigurationError


class FakeRuntime:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.shutdown_calls = 0

    def shutdown(self) -> None:
        self.shutdown_calls += 1
        self.events.append("runtime-shutdown")


class FakeApplication:
    def __init__(self, parser_factory=None) -> None:
        self.state = SimpleNamespace(document_parser_factory=parser_factory)


def test_lifespan_configures_runtime_and_shuts_it_down(monkeypatch):
    events: list[str] = []
    parser_factory = object()
    application = FakeApplication(parser_factory=parser_factory)
    runtime = FakeRuntime(events)

    @asynccontextmanager
    async def fake_base_lifespan(active_application):
        assert active_application is application
        events.append("base-start")
        try:
            yield
        finally:
            events.append("base-stop")

    def fake_configure(*, parser_factory):
        assert parser_factory is application.state.document_parser_factory
        events.append("runtime-configured")
        return runtime

    monkeypatch.setattr(main_module, "_base_lifespan", fake_base_lifespan)
    monkeypatch.setattr(
        main_module,
        "configure_document_parser_from_environment",
        fake_configure,
    )

    async def exercise() -> None:
        async with main_module._document_parser_lifespan(application):
            assert application.state.document_parser_runtime is runtime
            events.append("request-window")

    asyncio.run(exercise())

    assert runtime.shutdown_calls == 1
    assert events == [
        "base-start",
        "runtime-configured",
        "request-window",
        "runtime-shutdown",
        "base-stop",
    ]


def test_lifespan_blocks_unsafe_configuration_without_leaking_runtime(monkeypatch):
    events: list[str] = []
    application = FakeApplication()

    @asynccontextmanager
    async def fake_base_lifespan(_application):
        events.append("base-start")
        try:
            yield
        finally:
            events.append("base-stop")

    def fail_configuration(*, parser_factory):
        assert parser_factory is None
        raise DocumentParserConfigurationError("unsafe parser configuration")

    monkeypatch.setattr(main_module, "_base_lifespan", fake_base_lifespan)
    monkeypatch.setattr(
        main_module,
        "configure_document_parser_from_environment",
        fail_configuration,
    )

    async def exercise() -> None:
        async with main_module._document_parser_lifespan(application):
            raise AssertionError("lifespan must not start")

    with pytest.raises(DocumentParserConfigurationError, match="unsafe parser configuration"):
        asyncio.run(exercise())

    assert not hasattr(application.state, "document_parser_runtime")
    assert events == ["base-start", "base-stop"]


def test_main_app_uses_parser_lifespan():
    assert main_module.app.router.lifespan_context is main_module._document_parser_lifespan
