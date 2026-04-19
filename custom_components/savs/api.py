"""Sample API Client."""

from __future__ import annotations

import socket
import time
from typing import Any

import aiohttp
import async_timeout


class SavsApiClientError(Exception):
    """Exception to indicate a general API error."""


class SavsApiClientCommunicationError(SavsApiClientError):
    """Exception to indicate a communication error."""


class SavsApiClientAuthenticationError(SavsApiClientError):
    """Exception to indicate an authentication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise SavsApiClientAuthenticationError(msg)
    response.raise_for_status()


class SavsApiClient:
    """SAVS API Client."""

    def __init__(
        self,
        email: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """SAVS API Client."""
        self._email = email
        self._password = password
        self._session = session
        self._access_token = None

    async def test_credentials(self) -> Any:
        """Get data from the API."""
        # todo try to login
        return False

    async def async_get_data(self) -> Any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="get",
            url="https://jsonplaceholder.typicode.com/posts/1",
        )

    async def async_set_title(self, value: str) -> Any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="patch",
            url="https://jsonplaceholder.typicode.com/posts/1",
            data={"title": value},
            headers={"Content-type": "application/json; charset=UTF-8"},
        )

    def _get_common_headers(self) -> dict[str, str]:
        """Generate common headers for API requests."""
        timestamp = str(int(time.time() * 1000))
        nonce = f"app-{timestamp}-{timestamp}"

        return {
            "accept": "application/json",
            "accept-encoding": "gzip",
            "accept-language": "nl_NL",
            "apponshelves": "NL_OEM",
            "apptype": "0",
            "clienttype": "12",
            "content-type": "application/json",
            "nonce": nonce,
            "timeoffset": "-28800000",
            "timestamp": timestamp,
            "user-agent": "Dart/3.8 (dart:io)",
            "version": "v12",
            "wisualarmappid": "13",
        }

    def _validate_response(self, response: dict[str, Any]) -> None:
        """Validate that the API response is successful."""
        if not response.get("success") or response.get("code") != "0":
            msg = f"API request failed: {response.get('errMsg', 'Unknown error')}"
            raise SavsApiClientError(msg)

    async def get_user_list(self, param: str) -> str:
        """Get user list from the API and return the username."""
        try:
            data = {
                "retrieveFieldList": ["email"],
                "wisualarmAppIdList": ["13"],
                "param": param,
            }

            response = await self._api_wrapper(
                method="post",
                url="https://global.wisualarm.com/gateway/auth/user/getUserList",
                data=data,
                headers=self._get_common_headers(),
            )

            self._validate_response(response)
            user_list = response.get("data", [])

            if not user_list:
                msg = "No users found in response"
                raise SavsApiClientError(msg)

            if len(user_list) > 1:
                msg = f"Expected exactly one user, but found {len(user_list)} users"
                raise SavsApiClientError(msg)

            username = user_list[0].get("username")

            if username is None:
                msg = "Username field is missing in user data"
                raise SavsApiClientError(msg)

            return username

        except SavsApiClientError:
            raise
        except Exception as exception:
            msg = f"IO error fetching user list - {exception}"
            raise SavsApiClientCommunicationError(msg) from exception

    async def get_salt_and_random(self, username: str) -> dict[str, str]:
        """Get salt and random values for a username from the API."""
        try:
            url = f"https://global.wisualarm.com/gateway/auth/user/getSaltByUserName?username={username}"

            response = await self._api_wrapper(
                method="get",
                url=url,
                headers=self._get_common_headers(),
            )

            self._validate_response(response)
            data = response.get("data")

            if data is None:
                msg = "No data found in response"
                raise SavsApiClientError(msg)

            salt = data.get("salt")
            random = data.get("random")

            if salt is None or random is None:
                msg = "Salt or random field is missing in response data"
                raise SavsApiClientError(msg)

            return {"salt": salt, "random": random}

        except SavsApiClientError:
            raise
        except Exception as exception:
            msg = f"IO error fetching salt and random - {exception}"
            raise SavsApiClientCommunicationError(msg) from exception

    async def login(self, username: str, password: str) -> str:
        """Login to the API and return the access token."""
        try:
            # Build URL with query parameters
            url = (
                "https://global.wisualarm.com/gateway/auth/oauth/token"
                f"?password={password}"
                "&grant_type=password"
                "&scope=ui"
                "&client_id=oveasea_app"
                "&client_secret=browser"
                "&loginType=14"
                "&msgCode=null"
                "&telephone=null"
                f"&username={username}"
            )

            response = await self._api_wrapper(
                method="post",
                url=url,
                headers=self._get_common_headers(),
            )

            self._validate_response(response)
            data = response.get("data")

            if data is None:
                msg = "No data found in response"
                raise SavsApiClientError(msg)

            access_token = data.get("access_token")

            if access_token is None:
                msg = "Access token field is missing in response data"
                raise SavsApiClientError(msg)

            # Save the access token for future use
            self._access_token = access_token

            return access_token

        except SavsApiClientError:
            raise
        except Exception as exception:
            msg = f"IO error during login - {exception}"
            raise SavsApiClientCommunicationError(msg) from exception

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise SavsApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise SavsApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise SavsApiClientError(
                msg,
            ) from exception
