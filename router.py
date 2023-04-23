"""Provides the backend for a Cudy router"""

from datetime import timedelta
from typing import Any
import requests
import logging
import urllib.parse
from http.cookies import SimpleCookie

from .const import MODULE_DEVICES, MODULE_MODEM, OPTIONS_DEVICELIST
from .parser import parse_devices, parse_modem_info

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=15)
SCAN_INTERVAL = timedelta(seconds=30)
RETRY_INTERVAL = timedelta(seconds=300)


class CudyRouter:
    """Represents a router and provides functions for communication."""

    def __init__(
        self, hass: HomeAssistant, host: str, username: str, password: str
    ) -> None:
        """Initialize."""
        self.host = host
        self.auth_cookie = None
        self.hass = hass
        self.username = username
        self.password = password

    def get_cookie_header(self, force_auth: bool) -> str:
        """Returns a cookie header that should be used for authentication."""

        if not force_auth and self.auth_cookie:
            return f"sysauth={self.auth_cookie}"
        if self.authenticate():
            return f"sysauth={self.auth_cookie}"
        else:
            return ""

    def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""

        data_url = f"http://{self.host}/cgi-bin/luci"
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Cookie": ""}
        body = f"luci_username={urllib.parse.quote(self.username)}&luci_password={urllib.parse.quote(self.password)}&luci_language=en"

        try:
            response = requests.post(
                data_url, timeout=30, headers=headers, data=body, allow_redirects=False
            )
            if response.ok:
                cookie = SimpleCookie()
                cookie.load(response.headers.get("set-cookie"))
                self.auth_cookie = cookie.get("sysauth").value
                return True
        except requests.exceptions.ConnectionError:
            _LOGGER.debug("Connection error?")
        return False

    def get(self, url: str) -> str:
        """Retrieves data from the given URL using an authenticated session."""

        retries = 2
        while retries > 0:
            retries -= 1

            data_url = f"http://{self.host}/cgi-bin/luci/{url}"
            headers = {"Cookie": f"{self.get_cookie_header(False)}"}

            try:
                response = requests.get(
                    data_url, timeout=30, headers=headers, allow_redirects=False
                )
                if response.status_code == 403:
                    if self.authenticate():
                        continue
                    else:
                        _LOGGER.error("Error during authentication to %s", url)
                        break
                if response.ok:
                    return response.text
                else:
                    break
            except Exception:  # pylint: disable=broad-except
                pass

        _LOGGER.error("Error retrieving data from %s", url)
        return ""

    async def get_data(
        self, hass: HomeAssistant, options: dict[str, Any]
    ) -> dict[str, Any]:
        """Retrieves data from the router"""

        data: dict[str, Any] = {}

        data[MODULE_MODEM] = parse_modem_info(
            f"{await hass.async_add_executor_job(self.get, 'admin/network/gcom/status')}{await hass.async_add_executor_job(self.get, 'admin/network/gcom/status?detail=1')}"
        )
        data[MODULE_DEVICES] = parse_devices(
            await hass.async_add_executor_job(
                self.get, "admin/network/devices/devlist?detail=1"
            ),
            options and options.get(OPTIONS_DEVICELIST),
        )

        return data
