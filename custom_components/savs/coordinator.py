"""DataUpdateCoordinator for savs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SavsApiClientAuthenticationError,
    SavsApiClientCommunicationError,
    SavsApiClientError,
)

if TYPE_CHECKING:
    from .data import SavsConfigEntry


class SavsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: SavsConfigEntry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            page_data = await self.config_entry.runtime_data.client.async_get_devices()

            devices: list[dict[str, Any]] = []

            devices.extend(
                {
                    "device_id": main_device.get("deviceId"),
                    "name": main_device.get("name"),
                    "product_id": main_device.get("productId"),
                    "product_sub_type": main_device.get("productSubType"),
                    "model": main_device.get("productSubType"),
                    "pic_url": main_device.get("picUrl"),
                    "is_gateway": True,
                    "properties": main_device.get("properties", []),
                    "alarm_status": main_device.get("alarmStatus"),
                    "fault_status": main_device.get("faultStatus"),
                    "on_off_line_status": main_device.get("onOffLineStatus"),
                    "device_online_status": main_device.get("deviceOnlineStatus"),
                    "relation": main_device.get("relation"),
                }
                for main_device in page_data
            )

            devices.extend(
                {
                    "device_id": (
                        f"{sub_device.get('deviceId')}_{sub_device.get('subDeviceId')}"
                    ),
                    "name": sub_device.get("subDeviceName"),
                    "product_id": sub_device.get("subDeviceProductId"),
                    "product_sub_type": sub_device.get("subDeviceProductSubType"),
                    "model": sub_device.get("subDeviceModel"),
                    "pic_url": sub_device.get("picUrl"),
                    "is_gateway": False,
                    "parent_device_id": main_device.get("deviceId"),
                    "properties": sub_device.get("properties", []),
                    "alarm_status": sub_device.get("alarmStatus"),
                    "fault_status": sub_device.get("faultStatus"),
                    "on_off_line_status": sub_device.get("onOffLineStatus"),
                    "device_online_status": sub_device.get("deviceOnlineStatus"),
                }
                for main_device in page_data
                for sub_device in main_device.get("subDeviceList", [])
            )

            return {"devices": devices}  # noqa: TRY300

        except SavsApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except SavsApiClientCommunicationError as exception:
            raise ConfigEntryNotReady(exception) from exception
        except SavsApiClientError as exception:
            raise UpdateFailed(exception) from exception
        except Exception as err:
            msg = f"Error communicating with API: {err}"
            raise ConfigEntryNotReady(msg) from err
