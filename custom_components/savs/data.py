"""Custom types for savs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import SavsApiClient
    from .coordinator import BlueprintDataUpdateCoordinator


type SavsConfigEntry = ConfigEntry[SavsData]


@dataclass
class SavsData:
    """Data for the Blueprint integration."""

    client: SavsApiClient
    coordinator: BlueprintDataUpdateCoordinator
    integration: Integration
