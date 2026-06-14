# ruff: noqa: S101, PLR2004

"""Tests for the SAVS data update coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.savs.api import (
    SavsApiClientAuthenticationError,
    SavsApiClientCommunicationError,
    SavsApiClientError,
)
from custom_components.savs.const import LOGGER
from custom_components.savs.coordinator import SavsDataUpdateCoordinator
from custom_components.savs.data import SavsData

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

pytestmark = pytest.mark.asyncio


class FakeClient:
    """Minimal SAVS API client for coordinator tests."""

    def __init__(self, side_effect: BaseException | None = None) -> None:
        """Initialize the fake client."""
        self.async_get_devices = AsyncMock(side_effect=side_effect)


def coordinator_for_entry(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    client: FakeClient,
) -> SavsDataUpdateCoordinator:
    """Create a coordinator with a runtime entry."""
    coordinator = SavsDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name="savs",
        config_entry=entry,
        update_interval=None,
    )
    entry.runtime_data = SavsData(
        client=cast("Any", client),
        coordinator=coordinator,
        integration=Mock(),
    )
    return coordinator


async def test_async_update_data_transforms_gateway_and_sub_devices(
    hass: HomeAssistant,
    savs_config_entry: MockConfigEntry,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Test coordinator transformation of the representative device page."""
    client = FakeClient()
    client.async_get_devices.return_value = load_fixture("devices.json")["data"][
        "pageData"
    ]
    coordinator = coordinator_for_entry(hass, savs_config_entry, client)

    data = await coordinator._async_update_data()  # noqa: SLF001

    assert client.async_get_devices.await_count == 1
    assert len(data["devices"]) == 4
    gateway = data["devices"][0]
    first_sub_device = data["devices"][1]
    assert gateway["device_id"] == "CB07EB7RDE3669E"
    assert gateway["is_gateway"] is True
    assert "parent_device_id" not in gateway
    assert first_sub_device["device_id"] == "CB07EB7RDE3669E_BM0A6E6PDE91F77"
    assert first_sub_device["is_gateway"] is False
    assert first_sub_device["parent_device_id"] == "CB07EB7RDE3669E"
    assert first_sub_device["model"] == "S10-W"
    assert first_sub_device["name"] == "Rookmelder boven"


async def test_async_update_data_raises_auth_failed(
    hass: HomeAssistant,
    savs_config_entry: MockConfigEntry,
) -> None:
    """Test authentication errors are raised as config entry auth failures."""
    client = FakeClient(side_effect=SavsApiClientAuthenticationError("Invalid token"))
    coordinator = coordinator_for_entry(hass, savs_config_entry, client)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()  # noqa: SLF001


async def test_async_update_data_raises_update_failed_for_api_error(
    hass: HomeAssistant,
    savs_config_entry: MockConfigEntry,
) -> None:
    """Test API errors are raised as update failures."""
    client = FakeClient(side_effect=SavsApiClientError("API failed"))
    coordinator = coordinator_for_entry(hass, savs_config_entry, client)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()  # noqa: SLF001


async def test_async_update_data_raises_not_ready_for_communication_error(
    hass: HomeAssistant,
    savs_config_entry: MockConfigEntry,
) -> None:
    """Test communication errors are raised as config entry not ready."""
    client = FakeClient(side_effect=SavsApiClientCommunicationError("Connection failed"))
    coordinator = coordinator_for_entry(hass, savs_config_entry, client)

    with pytest.raises(ConfigEntryNotReady):
        await coordinator._async_update_data()  # noqa: SLF001


async def test_async_update_data_raises_not_ready_for_unexpected_error(
    hass: HomeAssistant,
    savs_config_entry: MockConfigEntry,
) -> None:
    """Test unexpected errors are raised as config entry not ready."""
    client = FakeClient(side_effect=RuntimeError("Unexpected failure"))
    coordinator = coordinator_for_entry(hass, savs_config_entry, client)

    with pytest.raises(ConfigEntryNotReady):
        await coordinator._async_update_data()  # noqa: SLF001
