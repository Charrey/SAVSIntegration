# ruff: noqa: S101

"""Tests for the SAVS integration lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState, current_entry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN, Platform
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.savs import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.savs.data import SavsData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.asyncio


class FakeClient:
    """Minimal SAVS API client for lifecycle tests."""

    def __init__(self) -> None:
        """Initialize the fake client."""
        self.async_get_devices = AsyncMock(return_value=[])


async def test_async_setup_entry_sets_up_sensor_platform(
    hass: HomeAssistant,
) -> None:
    """Test setup creates runtime data and forwards the sensor platform."""
    fake_client = FakeClient()
    savs_config_entry = MockConfigEntry(
        domain="savs",
        entry_id="01HXSAVSTEST00000000000000",
        title="user@example.com",
        unique_id="user-example-com",
        data={
            CONF_EMAIL: "user@example.com",
            CONF_PASSWORD: "secret-password",
            CONF_TOKEN: "test-access-token",
        },
        state=ConfigEntryState.SETUP_IN_PROGRESS,
    )

    with (
        patch("custom_components.savs.SavsApiClient", return_value=fake_client),
        patch(
            "custom_components.savs.async_get_clientsession",
            return_value=Mock(),
        ),
        patch(
            "custom_components.savs.async_get_loaded_integration",
            return_value=Mock(
                documentation="https://github.com/Charrey/SAVSIntegration"
            ),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=True),
        ) as async_forward_entry_setups,
    ):
        token = current_entry.set(savs_config_entry)
        try:
            result = await async_setup_entry(hass, savs_config_entry)
        finally:
            current_entry.reset(token)

    assert result is True
    assert isinstance(savs_config_entry.runtime_data, SavsData)
    assert savs_config_entry.runtime_data.client is fake_client
    async_forward_entry_setups.assert_awaited_once_with(
        savs_config_entry,
        [Platform.SENSOR],
    )


async def test_async_unload_entry_unloads_sensor_platform(
    hass: HomeAssistant,
    savs_config_entry: MockConfigEntry,
) -> None:
    """Test unload delegates to the config entry manager."""
    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        AsyncMock(return_value=True),
    ) as async_unload_platforms:
        result = await async_unload_entry(hass, savs_config_entry)

    assert result is True
    async_unload_platforms.assert_awaited_once_with(
        savs_config_entry,
        [Platform.SENSOR],
    )


async def test_async_reload_entry_reloads_entry(
    hass: HomeAssistant,
    savs_config_entry: MockConfigEntry,
) -> None:
    """Test reload delegates to the config entry manager."""
    with patch.object(
        hass.config_entries,
        "async_reload",
        AsyncMock(return_value=True),
    ) as async_reload:
        await async_reload_entry(hass, savs_config_entry)

    async_reload.assert_awaited_once_with(savs_config_entry.entry_id)
