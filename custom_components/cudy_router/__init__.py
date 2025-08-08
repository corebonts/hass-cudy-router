"""The Cudy Router integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import CudyRouterDataUpdateCoordinator
from .router import CudyRouter

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cudy Router from a config entry."""

    data = entry.data
    api = CudyRouter(hass, data[CONF_HOST], data[CONF_USERNAME], data[CONF_PASSWORD])
    coordinator = CudyRouterDataUpdateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            del hass.data[DOMAIN]
    return unload_ok
