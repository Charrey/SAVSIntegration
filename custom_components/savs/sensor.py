"""Sensor platform for savs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorEntity,  # ← already imported but NOT used in class def!
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import callback

from .const import LOGGER
from .entity import SavsEntity

if TYPE_CHECKING:
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
        key="zigbee_signal", name="Zigbee Signal", icon="mdi:signal"
    ),
)


async def async_setup_entry(
    entry: SavsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SAVS sensor platform."""
    coordinator = entry.runtime_data.coordinator

    all_devices = coordinator.data.get("devices", [])
    LOGGER.debug("=== async_setup_entry: total devices: %d ===", len(all_devices))

    # Only create battery/zigbee sensors for sub-devices (smoke detectors),
    # NOT the gateway — gateway has no battery or ZigbeeSignalStrength properties
    devices = [
        dev
        for dev in all_devices
        if dev.get("model") == "S10-W"  # Smoke detectors only
    ]
    LOGGER.debug("=== async_setup_entry: filtered devices: %d ===", len(devices))

    entities = [
        SavsSensor(
            coordinator=coordinator,
            device_data=device,
            description=description,
        )
        for device in devices
        for description in ENTITY_DESCRIPTIONS
    ]
    LOGGER.debug("=== async_setup_entry: total entities created: %d ===", len(entities))
    async_add_entities(entities)


class SavsSensor(SavsEntity, SensorEntity):
    """SAVS Sensor entity."""

    def __init__(
        self,
        coordinator: SavsDataUpdateCoordinator,
        device_data: dict[str, Any],
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        # Call super().__init__() FIRST before setting attributes (best practice)
        super().__init__(coordinator, device_data)

        self.entity_description = description
        device_name = device_data["name"]

        # Override the unique_id set by SavsEntity to include the sensor key,
        # and keep entry_id to avoid clashes if multiple accounts are added
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{self._device_id}_{description.key}"
        )
        self._attr_name = f"{device_name} {description.name}"

        # Set the initial native value from the data already in the coordinator
        self._attr_native_value = self._get_property_value(
            device_data.get("properties", []), description.key
        )

    @staticmethod
    def _get_property_value(
        properties: list[dict[str, Any]], key: str
    ) -> float | int | None:
        """Extract and cast a property value from a properties list."""
        identifier_map = {
            "battery": "batteryCapacity",
            "zigbee_signal": "ZigbeeSignalStrength",
        }
        identifier = identifier_map.get(key)
        if not identifier:
            return None

        for prop in properties:
            if prop.get("propertyIdentifier") == identifier:
                value = prop.get("propertyValue")
                if value is None:
                    return None
                if key == "battery":
                    return float(value)
                if key == "zigbee_signal":
                    return int(value)
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        LOGGER.debug(
            "=== _handle_coordinator_update called for %s / %s ===",
            self._device_id,
            self.entity_description.key,
        )
        device = self._device_data
        if device is None:
            LOGGER.warning("Device %s not found in coordinator data", self._device_id)
            return

        self._attr_native_value = self._get_property_value(
            device.get("properties", []), self.entity_description.key
        )
        LOGGER.debug(
            "  %s native_value → %r",
            self.entity_description.key,
            self._attr_native_value,
        )
        self.async_write_ha_state()

    @property
    def _device_data(self) -> dict[str, Any] | None:
        """Return the current device data from the coordinator."""
        for dev in self.coordinator.data.get("devices", []):
            if dev.get("device_id") == self._device_id:
                return dev
        return None
