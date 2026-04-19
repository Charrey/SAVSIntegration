"""Binary Sensor platform for savs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .entity import SavsEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SavsDataUpdateCoordinator
    from .data import SavsConfigEntry

# Define the description for the status sensor
BINARY_SENSOR_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="status",
        name="Status",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SavsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SAVS binary sensor platform."""
    coordinator = entry.runtime_data.coordinator

    # Filter for your relevant devices
    devices = [
        dev for dev in coordinator.data.get("devices", [])
        if dev.get("model") == "S10-W" or dev.get("product_sub_type") == "20041"
    ]

    entities = []
    for device in devices:
        for description in BINARY_SENSOR_DESCRIPTIONS:
            entities.append(
                SavsBinarySensor(
                    coordinator=coordinator,
                    device_data=device,
                    description=description
                )
            )

    async_add_entities(entities)


class SavsBinarySensor(SavsEntity):
    """SAVS Binary Sensor entity."""

    def __init__(
        self,
        coordinator: SavsDataUpdateCoordinator,
        device_data: dict[str, Any],
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, device_data, entity_type="binary_sensor")

        self._attr_device_id = device_data.get("device_id")
        self.entity_description = description
        self._attr_unique_id = f"{self._attr_device_id}_{description.key}"
        self._attr_name = f"{device_data['name']} {description.name}"

        # --- PICTURE LOGIC ---
        model = device_data.get("model")

        # Map your local static files here
        if model == "S10-W":
            self._attr_entity_picture = "/local/savs/s10w.png"
        elif "Gateway" in model:  # Adjust based on exact model string
            self._attr_entity_picture = "/local/savs/gateway.png"

    @property
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        # IMPLEMENTATION TIP:
        # If you want to check if the device is online/active, add logic here.
        # For example, checking a 'status' property in coordinator data.

        current_device = self._device_data
        if not current_device:
            return False

        # Example: Assuming you can determine online status
        # properties = current_device.get("properties", [])
        # for prop in properties:
        #     if prop.get("propertyIdentifier") == "status":
        #         return prop.get("propertyValue") == "active"

        # Default return True just to show the entity and its picture
        return True
