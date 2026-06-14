"""Button platform for savs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription

from .const import LOGGER
from .entity import SavsEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SavsDataUpdateCoordinator
    from .data import SavsConfigEntry

BUTTON_DESCRIPTIONS = (
    ButtonEntityDescription(
        key="node_test",
        name="Node Test",
        icon="mdi:bell-test",
    ),
)


# noinspection PyUnusedLocal
async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SavsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SAVS button platform."""
    coordinator = entry.runtime_data.coordinator
    gateway_devices = [
        device
        for device in coordinator.data.get("devices", [])
        if device.get("is_gateway")
    ]

    async_add_entities(
        SavsGatewayNodeTestButton(
            coordinator=coordinator,
            device_data=device,
            description=description,
        )
        for device in gateway_devices
        for description in BUTTON_DESCRIPTIONS
    )


class SavsGatewayNodeTestButton(SavsEntity, ButtonEntity):
    """SAVS gateway node test button."""

    def __init__(
        self,
        coordinator: SavsDataUpdateCoordinator,
        device_data: dict[str, Any],
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, device_data, entity_type="button")

        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{self._device_id}_{description.key}"
        )
        self._attr_name = f"{device_data['name']} {description.name}"

    async def async_press(self) -> None:
        """Trigger a node test on the gateway."""
        LOGGER.debug("Triggering node test for gateway %s", self._device_id)
        await self.coordinator.config_entry.runtime_data.client.async_test_alarm(
            self._device_id
        )
