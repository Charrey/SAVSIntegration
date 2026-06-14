# ruff: noqa: S101, S105, S106, PLR2004

"""Tests for the SAVS API client."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any, NoReturn
from unittest.mock import ANY

import aiohttp
import pytest
from yarl import URL

from custom_components.savs.api import (
    SavsApiClient,
    SavsApiClientAuthenticationError,
    SavsApiClientCommunicationError,
    SavsApiClientError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

BASE_URL = SavsApiClient.BASEURL
EXPECTED_ACCESS_TOKEN = "9bf982d1-c314-467e-b031-3a9cc53a3922"
HTTP_ERROR_STATUS = 400
NO_RESPONSE_MESSAGE = "No fake response configured"
NETWORK_FAILURE_MESSAGE = "network failure"
REQUEST_INFO = aiohttp.RequestInfo(
    url=URL("http://example.test"),
    method="GET",
    headers={},
)


class FakeResponse:
    """Minimal aiohttp response used by the API client."""

    def __init__(self, status: int, payload: Mapping[str, Any]) -> None:
        """Initialize the fake response."""
        self.status = status
        self._payload = payload

    def raise_for_status(self) -> None:
        """Raise for non-successful HTTP statuses."""
        if self.status >= HTTP_ERROR_STATUS:
            raise aiohttp.ClientResponseError(
                request_info=REQUEST_INFO,
                history=(),
                status=self.status,
                message="HTTP error",
            )

    async def json(self) -> Mapping[str, Any]:
        """Return the response payload."""
        return self._payload


class FakeSession:
    """Minimal aiohttp session used by the API client."""

    def __init__(self, responses: Sequence[FakeResponse]) -> None:
        """Initialize the fake session."""
        self.responses: deque[FakeResponse] = deque(responses)
        self.requests: list[tuple[str, str, dict[str, str] | None, Any]] = []

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
    ) -> FakeResponse:
        """Record and return the next fake response."""
        self.requests.append((method, url, headers, json))
        if not self.responses:
            raise AssertionError(NO_RESPONSE_MESSAGE)
        return self.responses.popleft()


class RaisingSession:
    """Session that raises an aiohttp client error."""

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
    ) -> NoReturn:
        """Raise a client error."""
        del method, url, headers, json
        raise aiohttp.ClientError(NETWORK_FAILURE_MESSAGE)


def response(status: int, payload: Mapping[str, Any]) -> FakeResponse:
    """Create a fake response."""
    return FakeResponse(status=status, payload=payload)


def assert_request_path(
    request: tuple[str, str, dict[str, str] | None, Any],
    expected_method: str,
    expected_path: str,
) -> URL:
    """Assert a request method and normalized URL path."""
    method, url, _headers, _json = request
    parsed_url = URL(url)
    assert method == expected_method
    assert parsed_url.raw_path.lstrip("/") == expected_path.lstrip("/")
    return parsed_url


def assert_login_request(
    request: tuple[str, str, dict[str, str] | None, Any],
) -> None:
    """Assert the login request endpoint and OAuth query parameters."""
    query = assert_request_path(
        request,
        "post",
        "/gateway/auth/oauth/token",
    ).query

    assert query["password"]
    assert query["grant_type"] == "password"
    assert query["scope"] == "ui"
    assert query["client_id"] == "oveasea_app"
    assert query["client_secret"] == "browser"
    assert query["loginType"] == "14"
    assert query["msgCode"] == "null"
    assert query["telephone"] == "null"
    assert query["username"] == "s7P9A0"


@pytest.mark.asyncio
async def test_test_credentials_returns_access_token(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Test the full login credential flow."""
    session = FakeSession(
        [
            response(200, load_fixture("user_list.json")),
            response(200, load_fixture("salt_random.json")),
            response(200, load_fixture("login_token.json")),
        ]
    )
    client = SavsApiClient(
        email="User@Example.com",
        password="secret-password",
        session=session,
    )

    token = await client.test_credentials()

    assert token == EXPECTED_ACCESS_TOKEN
    assert_request_path(
        session.requests[0],
        "post",
        "/gateway/auth/user/getUserList",
    )
    salt_query = assert_request_path(
        session.requests[1],
        "get",
        "/gateway/auth/user/getSaltByUserName",
    ).query
    assert salt_query["username"] == "s7P9A0"
    assert_login_request(session.requests[2])


@pytest.mark.asyncio
async def test_async_get_devices_returns_page_data(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Test fetching the device page."""
    session = FakeSession([response(200, load_fixture("devices.json"))])
    client = SavsApiClient(
        email="user@example.com",
        password="secret-password",
        session=session,
        access_token="test-access-token",
    )

    devices = await client.async_get_devices()

    assert len(devices) == 1
    assert devices[0]["deviceId"] == "CB07EB7RDE3669E"
    assert len(devices[0]["subDeviceList"]) == 3
    assert session.requests[0][2] == {
        "accept": "application/json",
        "accept-encoding": "gzip",
        "accept-language": "nl_NL",
        "apponshelves": "NL_OEM",
        "apptype": "0",
        "clienttype": "12",
        "content-type": "application/json",
        "nonce": ANY,
        "timeoffset": "-28800000",
        "timestamp": ANY,
        "user-agent": "Dart/3.8 (dart:io)",
        "version": "v12",
        "wisualarmappid": "13",
        "Authorization": "Bearer test-access-token",
    }


@pytest.mark.asyncio
async def test_async_get_devices_raises_authentication_error_on_invalid_token(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Test that an invalid token is surfaced as an authentication error."""
    session = FakeSession(
        [
            response(401, load_fixture("invalid_token.json")),
            response(200, load_fixture("user_list.json")),
            response(200, load_fixture("salt_random.json")),
            response(200, load_fixture("login_token.json")),
            response(401, load_fixture("invalid_token.json")),
        ],
    )
    client = SavsApiClient(
        email="user@example.com",
        password="secret-password",
        session=session,
        access_token="expired-token",
    )

    with pytest.raises(SavsApiClientAuthenticationError):
        await client.async_get_devices()


@pytest.mark.asyncio
async def test_async_get_devices_raises_api_error_on_failed_response() -> None:
    """Test that a failed API response raises the integration API error."""
    session = FakeSession(
        [
            response(
                200,
                {
                    "success": False,
                    "code": "1",
                    "errMsg": "参数错误",
                    "data": {},
                },
            )
        ]
    )
    client = SavsApiClient(
        email="user@example.com",
        password="secret-password",
        session=session,
    )

    with pytest.raises(SavsApiClientError):
        await client.async_get_devices()


@pytest.mark.asyncio
async def test_async_get_devices_raises_communication_error_on_client_error() -> None:
    """Test that aiohttp client errors are wrapped."""
    client = SavsApiClient(
        email="user@example.com",
        password="secret-password",
        session=RaisingSession(),
    )

    with pytest.raises(SavsApiClientCommunicationError):
        await client.async_get_devices()


@pytest.mark.asyncio
async def test_async_get_devices_retries_after_token_refresh(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Test retrying a device request after token refresh."""
    session = FakeSession(
        [
            response(401, load_fixture("invalid_token.json")),
            response(200, load_fixture("user_list.json")),
            response(200, load_fixture("salt_random.json")),
            response(200, load_fixture("login_token.json")),
            response(200, load_fixture("devices.json")),
        ]
    )
    client = SavsApiClient(
        email="user@example.com",
        password="secret-password",
        session=session,
        access_token="expired-token",
    )

    devices = await client.async_get_devices()

    assert len(devices) == 1
    assert [URL(request[1]).raw_path.lstrip("/") for request in session.requests] == [
        "gateway/consumerDevice/api/device/page",
        "gateway/auth/user/getUserList",
        "gateway/auth/user/getSaltByUserName",
        "gateway/auth/oauth/token",
        "gateway/consumerDevice/api/device/page",
    ]
    salt_query = URL(session.requests[2][1]).query
    assert salt_query["username"] == "s7P9A0"
    assert_login_request(session.requests[3])
    authorization = session.requests[-1][2]["Authorization"]
    assert authorization == f"Bearer {EXPECTED_ACCESS_TOKEN}"
