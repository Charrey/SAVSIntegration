"""Savs API Client."""
from __future__ import annotations

import hashlib
import hmac
import logging
import socket
import time
from typing import Any

import aiohttp
import async_timeout

from .const import LOGGER


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
        access_token: str | None = None,
    ) -> None:
        """SAVS API Client."""
        self._email = email
        self._password = password
        self._session = session
        self._access_token = access_token
        self._username_cache: str | None = None

    async def test_credentials(self) -> str:
        """
        Validate credentials by performing the full login flow.
        Returns the access token if successful.
        """
        try:
            self._username_cache = await self.get_user_list(self._email)
            salt_data = await self.get_salt_and_random(self._username_cache)
            hashed_password = self._hash_password(
                self._password,
                salt_data["salt"],
                salt_data["random"]
            )
            access_token = await self.login(self._username_cache, hashed_password)
            if not access_token:
                raise SavsApiClientAuthenticationError("No access token received")
            self._access_token = access_token
            return access_token

        except SavsApiClientAuthenticationError:
            raise
        except SavsApiClientCommunicationError:
            raise
        except Exception as err:
            LOGGER.exception("Unexpected error during validation")
            raise SavsApiClientError(f"Unexpected error during validation: {err}") from err

    async def async_get_data(self) -> Any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="get",
            url="https://jsonplaceholder.typicode.com/posts/1",
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

    def _hash_password(self, password: str, salt: str, random: str) -> str:
        inner_hash = hmac.new(
            key=salt.encode("utf-8"),
            msg=password.encode("utf-8"),
            digestmod=hashlib.md5,
        ).hexdigest()
        final_hash = hmac.new(
            key=random.encode("utf-8"),
            msg=inner_hash.encode("utf-8"),
            digestmod=hashlib.md5,
        ).hexdigest()
        return final_hash

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

            return access_token

        except SavsApiClientError:
            raise
        except Exception as exception:
            msg = f"IO error during login - {exception}"
            raise SavsApiClientCommunicationError(msg) from exception

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Fetch list of devices from the API."""
        try:
            data = {
                "roomId": "0",
                "pageNum": 1,
                "pageSize": 100
            }

            response = await self._api_wrapper(
                method="post",
                url="https://global.wisualarm.com/gateway/consumerDevice/api/device/page",
                data=data,
                headers=self._get_common_headers(),
            )

            self._validate_response(response)
            page_data = response.get("data", {}).get("pageData", [])

            return page_data

        except SavsApiClientError:
            raise
        except Exception as exception:
            msg = f"Error fetching devices - {exception}"
            raise SavsApiClientCommunicationError(msg) from exception

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API with automatic token refresh."""

        # Logic to attempt request twice (original + retry after refresh)
        for attempt in range(2):
            request_headers = headers.copy() if headers else {}
            if not headers:
                request_headers.update(self._get_common_headers())
            if self._access_token:
                request_headers["Authorization"] = f"Bearer {self._access_token}"
            try:
                async with async_timeout.timeout(10):
                    response = await self._session.request(
                        method=method,
                        url=url,
                        headers=request_headers,
                        json=data,
                    )
                    payload = await response.json()
                    if response.status in (401, 403):
                        raise SavsApiClientAuthenticationError("Invalid credentials or token expired")
                    if response.status == 200:
                        self._validate_response(payload)
                    return payload

            except TimeoutError as exception:
                msg = f"Timeout error fetching information - {exception}"
                raise SavsApiClientCommunicationError(msg) from exception
            except (aiohttp.ClientError, socket.gaierror) as exception:
                msg = f"Error fetching information - {exception}"
                raise SavsApiClientCommunicationError(msg) from exception
            except SavsApiClientAuthenticationError as exception:
                # If we get a 401/403 error on the first attempt, try to refresh token
                if attempt == 0 and self._email and self._password:
                    LOGGER.info("Authentication failed (401/403), attempting token refresh...")
                    await self.test_credentials()
                    continue
                else:
                    # If we already retried or have no credentials to refresh, raise error
                    msg = f"Authentication failed after refresh - {exception}"
                    raise SavsApiClientAuthenticationError(msg) from exception

            except Exception as exception:  # pylint: disable=broad-except
                msg = f"Something really wrong happened! - {exception}"
                raise SavsApiClientError(msg) from exception
