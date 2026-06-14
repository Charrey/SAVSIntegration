"""Test fixtures for the SAVS Home Assistant integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.savs.const import DOMAIN

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator

    from homeassistant.core import HomeAssistant

pytest_plugins = "pytest_homeassistant_custom_component"

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture() -> Callable[[str], dict[str, Any]]:
    """Load a JSON fixture from the tests/fixtures directory."""

    def _load_fixture(name: str) -> dict[str, Any]:
        return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    return _load_fixture


@pytest.fixture
def savs_config_entry() -> MockConfigEntry:
    """Return a SAVS config entry with representative data."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="01HXSAVSTEST00000000000000",
        title="user@example.com",
        unique_id="user-example-com",
        data={
            CONF_EMAIL: "user@example.com",
            CONF_PASSWORD: "secret-password",
            CONF_TOKEN: "test-access-token",
        },
        state=ConfigEntryState.LOADED,
    )


@pytest.fixture
async def mock_setup_entry(hass: HomeAssistant) -> AsyncIterator[Any]:
    """Prevent real integration setup during config-flow tests."""
    del hass
    with patch("custom_components.savs.async_setup_entry") as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_integration() -> Iterator[Mock]:
    """Return a minimal integration object for loader-dependent code."""
    integration = Mock()
    integration.documentation = "https://github.com/Charrey/SAVSIntegration"
    with (
        patch(
            "custom_components.savs.config_flow.async_get_loaded_integration",
            return_value=integration,
        ),
        patch(
            "custom_components.savs.async_get_loaded_integration",
            return_value=integration,
        ),
    ):
        yield integration


@pytest.fixture
def mock_clientsession() -> Iterator[Mock]:
    """Return a fake aiohttp client session."""
    session = Mock()
    with (
        patch(
            "custom_components.savs.api.async_get_clientsession",
            return_value=session,
        ),
        patch(
            "custom_components.savs.config_flow.async_create_clientsession",
            return_value=session,
        ),
    ):
        yield session
