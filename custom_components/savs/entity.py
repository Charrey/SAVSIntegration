"""SavsEntity class."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import SavsDataUpdateCoordinator


class SavsEntity(CoordinatorEntity[SavsDataUpdateCoordinator]):
    """SavsEntity class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SavsDataUpdateCoordinator,
        device_data: dict[str, Any],
        entity_type: str = "sensor",
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        self._device_id = device_data["device_id"]

        # Set unique_id combining entry_id and device_id
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{self._device_id}_{entity_type}"
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_data["name"],
            manufacturer="SAVS",
            model=device_data.get("model", "Unknown"),
            suggested_area=device_data.get("room_name"),
            via_device=(DOMAIN, device_data.get("parent_device_id"))
            if device_data.get("parent_device_id")
            else None,
        )

        self._attr_extra_state_attributes = {
            "device_id": device_data["device_id"],
            "product_id": device_data["product_id"],
            "product_sub_type": device_data["product_sub_type"],
        }
