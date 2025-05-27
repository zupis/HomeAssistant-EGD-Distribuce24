"""The EGD-Distribuce24 integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS 

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the EGD-Distribuce24 component. This is not used for config flow."""
    _LOGGER.info(f"Async_setup for {DOMAIN}: No YAML config to process.")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EGD-Distribuce24 from a config entry."""
    _LOGGER.info(f"Setting up {DOMAIN} for config entry: {entry.title} ({entry.entry_id})")
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data 

    # Corrected way to forward entry setups
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info(f"Finished setting up {DOMAIN} for config entry: {entry.title}")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f"Unloading {DOMAIN} for config entry: {entry.title} ({entry.entry_id})")
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Clean up hass.data[DOMAIN] if it's empty or only contains structure keys
        if not hass.data[DOMAIN].get('entries') and not any(k.endswith("_initial_recorder_delay_done") for k in hass.data[DOMAIN]):
             hass.data.pop(DOMAIN, None)
        elif not hass.data[DOMAIN].get('entries') and all(k.endswith("_initial_recorder_delay_done") for k in hass.data[DOMAIN]): # only delay flags left
             # This part is tricky, decide if domain specific data should be completely removed if only flags are left
             pass # Or pop if truly empty otherwise

        _LOGGER.info(f"Successfully unloaded {DOMAIN} for config entry: {entry.title}")
    else:
        _LOGGER.error(f"Failed to unload platforms for {DOMAIN} entry: {entry.title}")

    return unload_ok
