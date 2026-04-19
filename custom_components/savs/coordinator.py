"""DataUpdateCoordinator for savs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SavsApiClientAuthenticationError,
    SavsApiClientError,
)

if TYPE_CHECKING:
    from .data import SavsConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class SavsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: SavsConfigEntry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Access client via runtime_data
            page_data = await self.config_entry.runtime_data.client.async_get_devices()

            # Extract all devices (main + sub-devices)
            devices = []

            for main_device in page_data:
                # Add main device
                devices.append({
                    "device_id": main_device.get("deviceId"),
                    "name": main_device.get("name"),
                    "product_id": main_device.get("productId"),
                    "product_sub_type": main_device.get("productSubType"),
                    "model": main_device.get("productSubType"),
                    "pic_url": main_device.get("picUrl"),
                    "is_gateway": True,
                    "properties": main_device.get("properties", [])
                })

                # Add sub-devices
                for sub_device in main_device.get("subDeviceList", []):
                    devices.append({
                        "device_id": f"{sub_device.get('deviceId')}_{sub_device.get('subDeviceId')}",
                        "name": sub_device.get("subDeviceName"),
                        "product_id": sub_device.get("subDeviceProductId"),
                        "product_sub_type": sub_device.get("subDeviceProductSubType"),
                        "model": sub_device.get("subDeviceModel"),
                        "pic_url": sub_device.get("picUrl"),
                        "is_gateway": False,
                        "parent_device_id": main_device.get("deviceId"),
                        "properties": main_device.get("properties", [])
                    })

            return {"devices": devices}

        except SavsApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except SavsApiClientError as exception:
            raise UpdateFailed(exception) from exception
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
