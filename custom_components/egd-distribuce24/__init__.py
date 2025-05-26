"""The EGD-Distribuce24 integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS 

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the EGD-Distribuce24 component. This is not used for config flow."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info("Async_setup for EGD-Distribuce24: No YAML config to process.")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EGD-Distribuce24 from a config entry."""
    _LOGGER.info(f"Setting up EGD-Distribuce24 for config entry: {entry.title} ({entry.entry_id})")
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data 

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info(f"Finished setting up EGD-Distribuce24 for config entry: {entry.title}")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f"Unloading EGD-Distribuce24 for config entry: {entry.title} ({entry.entry_id})")
    
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, PLATFORMS[0]) # Assuming only "sensor" platform

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None) 
        _LOGGER.info(f"Successfully unloaded EGD-Distribuce24 for config entry: {entry.title}")
    else:
        _LOGGER.error(f"Failed to unload sensor platform for EGD-Distribuce24 entry: {entry.title}")

    return unload_ok

