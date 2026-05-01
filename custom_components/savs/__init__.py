"""
Custom integration to integrate SAVS alarms with Home Assistant.

For more details about this integration, please refer to
https://github.com/Charrey/SAVSIntegration
"""

from __future__ import annotations

import pathlib
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN, Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import SavsApiClient
from .const import DOMAIN, LOGGER
from .coordinator import SavsDataUpdateCoordinator
from .data import SavsData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .data import SavsConfigEntry


PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up the SAVS component and register static assets."""
    integration_path = pathlib.Path(__file__).parent
    images_path = integration_path / "images"

    # Use hass.async_add_executor_job for blocking file operations
    def check_dir() -> bool:
        return images_path.is_dir()

    if await hass.async_add_executor_job(check_dir) and hass.http:
        await hass.http.async_register_static_paths(
            [StaticPathConfig("/local/savs", str(images_path))]
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
        update_interval=timedelta(seconds=5),
    )
    entry.runtime_data = SavsData(
        client=SavsApiClient(
            email=entry.data[CONF_EMAIL],
            password=entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
            access_token=entry.data.get(CONF_TOKEN),
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
