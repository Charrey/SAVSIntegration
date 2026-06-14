"""Sensor platform for savs."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import callback

from .const import LOGGER
from .entity import SavsEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SavsDataUpdateCoordinator
    from .data import SavsConfigEntry

PROPERTY_SENSOR_DESCRIPTIONS = (
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
        device_class=SensorDeviceClass.ENUM,
    ),
)
CONNECTIVITY_DESCRIPTION = SensorEntityDescription(
    key="connectivity",
    name="Connectivity",
    icon="mdi:wifi",
    device_class=SensorDeviceClass.ENUM,
    options=("Online", "Offline"),
)
FIRE_DETECTED_DESCRIPTION = SensorEntityDescription(
    key="fire_detected",
    name="Fire Detected",
    icon="mdi:fire",
)


# noinspection PyUnusedLocal
async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SavsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SAVS sensor platform."""
    coordinator = entry.runtime_data.coordinator

    all_devices = coordinator.data.get("devices", [])
    LOGGER.debug("=== async_setup_entry: total devices: %d ===", len(all_devices))

    # Only create battery/zigbee sensors for sub-devices (smoke detectors),
    # NOT the gateway — gateway has no battery or ZigbeeSignalStrength properties
    smoke_detector_devices = [dev for dev in all_devices if dev.get("model") == "S10-W"]
    LOGGER.debug(
        "=== async_setup_entry: filtered devices: %d smoke detectors, %d total ===",
        len(smoke_detector_devices),
        len(all_devices),
    )

    entities = [
        SavsSensor(
            coordinator=coordinator,
            device_data=device,
            description=description,
        )
        for device in smoke_detector_devices
        for description in PROPERTY_SENSOR_DESCRIPTIONS
    ]
    entities.extend(
        SavsSensor(
            coordinator=coordinator,
            device_data=device,
            description=FIRE_DETECTED_DESCRIPTION,
        )
        for device in smoke_detector_devices
    )
    entities.extend(
        SavsSensor(
            coordinator=coordinator,
            device_data=device,
            description=CONNECTIVITY_DESCRIPTION,
        )
        for device in all_devices
    )
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

        # Override the unique_id set by SavsEntity to include the sensor key,
        # and keep entry_id to avoid clashes if multiple accounts are added
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{self._device_id}_{description.key}"
        )
        self._attr_name = description.name

        # For enum sensors, set options dynamically from propertyProtocol
        if description.key == "zigbee_signal":
            properties = device_data.get("properties", [])
            for prop in properties:
                if prop.get("propertyIdentifier") == "ZigbeeSignalStrength":
                    enum_mapping = self._parse_enum_protocol(
                        prop.get("propertyProtocol")
                    )
                    if enum_mapping:
                        self._attr_options = list(enum_mapping.values())
                    break

        # Set the initial native value from the data already in the coordinator
        self._attr_native_value = self._get_property_value(device_data, description.key)

    @staticmethod
    def _get_on_off_line_status(value: Any) -> str | None:
        """Convert an onOffLineStatus value to online/offline."""
        return "Online" if value == 1 else "Offline" if value == 0 else None

    @staticmethod
    def _parse_enum_protocol(protocol: str | None) -> dict[str, str] | None:
        """Parse propertyProtocol JSON to extract enum mapping."""
        if not protocol:
            return None
        try:
            protocol_data = json.loads(protocol)
            type_json = protocol_data.get("typeJson")
            if not type_json:
                return None
            return json.loads(type_json)
        except json.JSONDecodeError, TypeError:
            return None

    @classmethod
    def _get_property_value(
        cls, device_data: dict[str, Any], key: str
    ) -> float | int | str | bool | None:
        """Extract and cast a property value from device data."""
        if key == "connectivity":
            return cls._get_connectivity_value(device_data)
        if key == "fire_detected":
            return cls._get_fire_detected_value(device_data)
        return cls._get_sensor_property_value(device_data, key)

    @classmethod
    def _get_connectivity_value(cls, device_data: dict[str, Any]) -> str | None:
        """Extract connectivity sensor value."""
        return cls._get_on_off_line_status(device_data.get("on_off_line_status"))

    @classmethod
    def _get_fire_detected_value(cls, device_data: dict[str, Any]) -> bool | None:
        """Extract fire detected sensor value."""
        alarm_status = device_data.get("alarm_status")
        if alarm_status is None:
            return None
        return alarm_status == 0

    @classmethod
    def _get_sensor_property_value(
        cls, device_data: dict[str, Any], key: str
    ) -> float | int | str | None:
        """Extract a value from a device property."""
        property_identifier = {
            "battery": "batteryCapacity",
            "zigbee_signal": "ZigbeeSignalStrength",
        }.get(key)
        if not property_identifier:
            return None

        for prop in device_data.get("properties", []):
            if prop.get("propertyIdentifier") == property_identifier:
                return cls._get_sensor_property_value_from_protocol(prop, key)
        return None

    @staticmethod
    def _get_sensor_property_value_from_protocol(
        prop: dict[str, Any], key: str
    ) -> float | int | str | None:
        """Extract and cast a value from a property protocol entry."""
        value = prop.get("propertyValue")
        if value is None:
            return None
        if key == "battery":
            return float(value)
        if key == "zigbee_signal":
            enum_mapping = SavsSensor._parse_enum_protocol(prop.get("propertyProtocol"))
            if enum_mapping:
                return enum_mapping.get(str(value), str(value))
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

        # For enum sensors, update options dynamically from propertyProtocol
        if self.entity_description.key == "zigbee_signal":
            properties = device.get("properties", [])
            for prop in properties:
                if prop.get("propertyIdentifier") == "ZigbeeSignalStrength":
                    enum_mapping = self._parse_enum_protocol(
                        prop.get("propertyProtocol")
                    )
                    if enum_mapping:
                        self._attr_options = list(enum_mapping.values())
                    break

        self._attr_native_value = self._get_property_value(
            device, self.entity_description.key
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
