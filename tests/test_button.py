# ruff: noqa: S101

"""Tests for the SAVS button platform."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.components.button import ButtonEntityDescription

from custom_components.savs.button import SavsGatewayNodeTestButton, async_setup_entry
from custom_components.savs.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

GATEWAY_ID = "CB07EB7RDE3669E"

pytestmark = pytest.mark.asyncio


class FakeCoordinator:
    """Minimal coordinator for button tests."""

    def __init__(self, entry: MockConfigEntry, data: dict[str, Any]) -> None:
        """Initialize the fake coordinator."""
        self.config_entry = entry
        self.data = data


def device_id_for(entity: SavsGatewayNodeTestButton) -> str:
    """Return the SAVS device id from an entity's device info."""
    identifiers = cast("set[tuple[str, str]]", entity.device_info["identifiers"])
    domain, device_id = next(iter(identifiers))
    assert domain == DOMAIN
    return device_id


async def test_async_setup_entry_creates_gateway_node_test_button(
    hass: HomeAssistant,
    savs_config_entry: MockConfigEntry,
) -> None:
    """Test that button setup creates a node test button for the gateway."""
    del hass
    gateway = {
        "device_id": GATEWAY_ID,
        "name": "Draadloze gateway",
        "product_id": "MYVMQXD5",
        "product_sub_type": "20041",
        "model": "20041",
        "is_gateway": True,
    }
    coordinator = FakeCoordinator(savs_config_entry, {"devices": [gateway]})
    client = Mock()
    client.async_test_alarm = AsyncMock()
    savs_config_entry.runtime_data = Mock(coordinator=coordinator, client=client)
    added_entities: list[SavsGatewayNodeTestButton] = []

    await async_setup_entry(
        hass=Mock(),
        entry=cast("Any", savs_config_entry),
        async_add_entities=added_entities.extend,
    )

    assert len(added_entities) == 1
    button = added_entities[0]
    assert device_id_for(button) == GATEWAY_ID
    assert button.name == "Node Test"
    assert button.unique_id == "01HXSAVSTEST00000000000000_CB07EB7RDE3669E_node_test"


async def test_node_test_button_press_calls_api(
    savs_config_entry: MockConfigEntry,
) -> None:
    """Test that pressing the node test button calls the API."""
    gateway = {
        "device_id": GATEWAY_ID,
        "name": "Draadloze gateway",
        "product_id": "MYVMQXD5",
        "product_sub_type": "20041",
        "model": "20041",
        "is_gateway": True,
    }
    coordinator = FakeCoordinator(savs_config_entry, {"devices": [gateway]})
    client = Mock()
    client.async_test_alarm = AsyncMock()
    savs_config_entry.runtime_data = Mock(coordinator=coordinator, client=client)
    button = SavsGatewayNodeTestButton(
        coordinator=cast("Any", coordinator),
        device_data=gateway,
        description=ButtonEntityDescription(key="node_test", name="Node Test"),
    )

    await button.async_press()

    client.async_test_alarm.assert_awaited_once_with(GATEWAY_ID)
