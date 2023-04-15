"""Provides the backend for a Cudy router"""

from datetime import timedelta
from typing import Any
import requests
import logging
import urllib.parse
from http.cookies import SimpleCookie
from .parser import parse_devices, parse_modem_info

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=15)
SCAN_INTERVAL = timedelta(seconds=30)
RETRY_INTERVAL = timedelta(seconds=300)

SAMPLE_DATA = {
    "modem": {
        "network": {"value": "Yettel HU", "attributes": {"MCC": "216", "MNC": "01"}},
        "uptime": {"value": 3600, "unit": "seconds"},
        "cell": {
            "value": 54103,
            "attributes": {"ID": 54103, "eNB": 211, "Sector": 87, "PCID": 260},
        },
        "signal": {
            "value": 3,
            "attributes": {"RSSI": 20, "RSRP": -107, "RSRQ": -13, "SINR": 9},
        },
        "band": {
            "value": "B3",
            "attributes": {
                "DL Bandwidth": 20,
                "UL Bandwidth": 20,
                "PCC": "B3",
                "PCC DL Bandwidth": 20,
                "PCC UL Bandwidth": 20,
                "SCC": "B20",
                "SCC DL Bandwidth": 5,
                "SCC UL Bandwidth": 5,
            },
        },
    }
}


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
            except Exception:
                pass

        _LOGGER.error("Error retrieving data from %s", url)
        return ""

    async def get_data(
        self, hass: HomeAssistant, options: dict[str, Any]
    ) -> dict[str, Any]:
        """Retrieves data from the router"""

        data: dict[str, Any] = {}

        data["modem"] = parse_modem_info(
            f"{await hass.async_add_executor_job(self.get, 'admin/network/gcom/status')}{await hass.async_add_executor_job(self.get, 'admin/network/gcom/status?detail=1')}"
        )
        data["devices"] = parse_devices(
            await hass.async_add_executor_job(
                self.get, "admin/network/devices/devlist?detail=1"
            ),
            options and options.get("device_list"),
        )

        return data
