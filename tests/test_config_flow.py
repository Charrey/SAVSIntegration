# ruff: noqa: S101

"""Tests for the SAVS config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import data_entry_flow, loader
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN

from custom_components.savs.api import (
    SavsApiClientAuthenticationError,
    SavsApiClientCommunicationError,
    SavsApiClientError,
)
from custom_components.savs.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def enable_custom_integrations(hass: HomeAssistant) -> None:
    """Enable custom integrations defined in the test dir."""
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)


async def test_form_creates_entry(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_integration: object,
) -> None:
    """Test the user form creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM

    with patch(
        "custom_components.savs.config_flow.SavsApiClient.test_credentials",
        new=AsyncMock(return_value="test-access-token"),
    ) as test_credentials:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "User@Example.com",
                CONF_PASSWORD: "secret-password",
            },
        )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@example.com"
    assert result["data"][CONF_EMAIL] == "user@example.com"
    assert result["data"][CONF_PASSWORD] == "secret-password"
    assert result["data"][CONF_TOKEN] == "test-access-token"
    assert test_credentials.await_count == 1
    assert mock_setup_entry.await_count == 1
    assert mock_integration is not None


async def test_invalid_email_does_not_call_api(
    hass: HomeAssistant,
    mock_integration: object,
) -> None:
    """Test that invalid email input is rejected before API validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    with patch(
        "custom_components.savs.config_flow.SavsApiClient.test_credentials",
    ) as test_credentials:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "not-an-email",
                CONF_PASSWORD: "secret-password",
            },
        )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_email"}
    test_credentials.assert_not_awaited()
    assert mock_integration is not None


async def test_authentication_error(
    hass: HomeAssistant,
    mock_integration: object,
) -> None:
    """Test authentication failures are shown as auth errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    with patch(
        "custom_components.savs.config_flow.SavsApiClient.test_credentials",
        new=AsyncMock(
            side_effect=SavsApiClientAuthenticationError("Invalid credentials")
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "user@example.com",
                CONF_PASSWORD: "wrong-password",
            },
        )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}
    assert mock_integration is not None


async def test_connection_error(
    hass: HomeAssistant,
    mock_integration: object,
) -> None:
    """Test communication failures are shown as connection errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    with patch(
        "custom_components.savs.config_flow.SavsApiClient.test_credentials",
        new=AsyncMock(
            side_effect=SavsApiClientCommunicationError("Network unavailable")
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "user@example.com",
                CONF_PASSWORD: "secret-password",
            },
        )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "connection"}
    assert mock_integration is not None


async def test_already_configured(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_integration: object,
) -> None:
    """Test that a second account with the same email is rejected."""
    first_result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    with patch(
        "custom_components.savs.config_flow.SavsApiClient.test_credentials",
        new=AsyncMock(return_value="first-token"),
    ):
        first_result = await hass.config_entries.flow.async_configure(
            first_result["flow_id"],
            {
                CONF_EMAIL: "user@example.com",
                CONF_PASSWORD: "secret-password",
            },
        )

    assert first_result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY

    second_result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    with patch(
        "custom_components.savs.config_flow.SavsApiClient.test_credentials",
        new=AsyncMock(return_value="second-token"),
    ):
        second_result = await hass.config_entries.flow.async_configure(
            second_result["flow_id"],
            {
                CONF_EMAIL: "USER@example.com",
                CONF_PASSWORD: "another-password",
            },
        )

    assert second_result["type"] is data_entry_flow.FlowResultType.ABORT
    assert second_result["reason"] == "already_configured"
    assert mock_setup_entry.await_count == 1
    assert mock_integration is not None


async def test_unknown_error(
    hass: HomeAssistant,
    mock_integration: object,
) -> None:
    """Test generic API errors are shown as unknown errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    with patch(
        "custom_components.savs.config_flow.SavsApiClient.test_credentials",
        new=AsyncMock(
            side_effect=SavsApiClientError("Unexpected API error")
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "user@example.com",
                CONF_PASSWORD: "secret-password",
            },
        )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}
    assert mock_integration is not None


async def test_error_recovery(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_integration: object,
) -> None:
    """Test that user can recover from an error and complete the flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    # First attempt fails with authentication error
    with patch(
        "custom_components.savs.config_flow.SavsApiClient.test_credentials",
        new=AsyncMock(
            side_effect=SavsApiClientAuthenticationError("Invalid credentials")
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "user@example.com",
                CONF_PASSWORD: "wrong-password",
            },
        )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}

    # Second attempt succeeds with correct credentials
    with patch(
        "custom_components.savs.config_flow.SavsApiClient.test_credentials",
        new=AsyncMock(return_value="recovered-access-token"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "user@example.com",
                CONF_PASSWORD: "correct-password",
            },
        )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@example.com"
    assert result["data"][CONF_EMAIL] == "user@example.com"
    assert result["data"][CONF_PASSWORD] == "correct-password"
    assert result["data"][CONF_TOKEN] == "recovered-access-token"
    assert mock_setup_entry.await_count == 1
    assert mock_integration is not None
