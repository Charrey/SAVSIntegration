"""Sensor platform for savs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE

from .entity import SavsEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SavsDataUpdateCoordinator
    from .data import SavsConfigEntry

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="battery",
        name="Battery",
        icon="mdi:battery",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="zigbee_signal",
        name="Zigbee Signal",
        icon="mdi:signal",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SavsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SAVS sensor platform."""
    coordinator = entry.runtime_data.coordinator

    # Filter devices that are S10-W smoke detectors OR G10 Gateways
    devices = [
        dev for dev in coordinator.data.get("devices", [])
        if dev.get("model") == "S10-W" or dev.get("product_sub_type") == "20041"
    ]

    entities = []
    for device in devices:
        for description in ENTITY_DESCRIPTIONS:
            entities.append(
                SavsSensor(
                    coordinator=coordinator,
                    device_data=device,
                    description=description
                )
            )

    async_add_entities(entities)


class SavsSensor(SavsEntity):
    """SAVS Sensor entity."""

    def __init__(
        self,
        coordinator: SavsDataUpdateCoordinator,
        device_data: dict[str, Any],
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self._device_id = device_data["device_id"]  # Store ID to look up fresh data
        device_name = device_data["name"]
        super().__init__(coordinator, device_data)

        self.entity_description = description
        self._attr_unique_id = f"{self._device_id}_{description.key}"
        self._attr_name = f"{device_name} {description.name}"

        if device_data.get("pic_url"):
            self._attr_entity_picture = device_data["pic_url"]

    @property
    def _device_data(self) -> dict[str, Any] | None:
        """Return the current device data from the coordinator."""
        # Dynamically lookup the device by ID to ensure we get fresh data on every update
        devices = self.coordinator.data.get("devices", [])
        for dev in devices:
            if dev.get("device_id") == self._device_id:
                return dev
        return None

    def _get_property(self, identifier: str) -> str | int | None:
        """Get property value from device data."""
        current_data = self._device_data
        if not current_data:
            return None

        properties = current_data.get("properties", [])
        for prop in properties:
            if prop.get("propertyIdentifier") == identifier:
                return prop.get("propertyValue")
        return None

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor."""
        if self.entity_description.key == "battery":
            battery = self._get_property("batteryCapacity")
            return float(battery) if battery else None
        if self.entity_description.key == "zigbee_signal":
            signal = self._get_property("ZigbeeSignalStrength")
            return int(signal) if signal else None
        return None
