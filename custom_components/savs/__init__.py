"""
Custom integration to integrate SAVS alarms with Home Assistant.

For more details about this integration, please refer to
https://github.com/Charrey/SAVSIntegration
"""

from __future__ import annotations

import os
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_EMAIL, CONF_TOKEN, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_loaded_integration
from homeassistant.components.http import StaticPathConfig

from .api import SavsApiClient
from .const import DOMAIN, LOGGER
from .coordinator import SavsDataUpdateCoordinator
from .data import SavsData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import SavsConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR#,
    #Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the SAVS component and register static assets."""

    integration_path = os.path.dirname(__file__)
    images_path = os.path.join(integration_path, "images")

    if os.path.isdir(images_path):
        if hass.http:
            # Use StaticPathConfig dataclass here
            await hass.http.async_register_static_paths(
                [StaticPathConfig("/local/savs", images_path)]
            )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SavsConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = SavsDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(hours=1),
    )
    entry.runtime_data = SavsData(
        client=SavsApiClient(
            email=entry.data[CONF_EMAIL],
            password=entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
            access_token=entry.data.get(CONF_TOKEN)
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: SavsConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: SavsConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
