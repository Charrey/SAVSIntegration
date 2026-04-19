"""Adds config flow for Blueprint."""

from __future__ import annotations

import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_EMAIL
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.loader import async_get_loaded_integration
from slugify import slugify

from .api import (
    SavsApiClient,
    SavsApiClientAuthenticationError,
    SavsApiClientCommunicationError,
    SavsApiClientError,
)
from .const import DOMAIN, LOGGER


class SavsFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Savs."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                email = user_input[CONF_EMAIL].lower()

                # Validate email format
                if not self._is_valid_email(email):
                    _errors["base"] = "invalid_email"
                else:
                    await self._test_credentials(
                        email=email,
                        password=user_input[CONF_PASSWORD],
                    )

                    await self.async_set_unique_id(
                        unique_id=slugify(email)
                    )
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=email,
                        data={**user_input, CONF_EMAIL: email},
                    )

            except SavsApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except SavsApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except SavsApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, (  # noqa: S101
            "Integration documentation URL is not set in manifest.json"
        )

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "documentation_url": integration.documentation,
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL,
                        default=(user_input or {}).get(CONF_EMAIL, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format using regex."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    async def _test_credentials(self, email: str, password: str) -> None:
        """Validate credentials."""
        client = SavsApiClient(
            email=email,
            password=password,
            session=async_create_clientsession(self.hass),
        )
        await client.test_credentials()
