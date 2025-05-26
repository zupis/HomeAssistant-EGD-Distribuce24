"""Config flow for EGD-Distribuce24 integration."""
import logging
import voluptuous as vol
import asyncio 

from homeassistant import config_entries
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession 

from .const import (
    DOMAIN,
    CONF_EAN,
    CONF_DAYS_OFFSET,
    CONF_MAX_FETCH_DAYS, 
    CONF_CREATE_CONSUMPTION_SENSORS, # New
    CONF_CREATE_PRODUCTION_SENSORS,  # New
    DEFAULT_DAYS_OFFSET,
    DEFAULT_MAX_FETCH_DAYS, 
    DEFAULT_CREATE_CONSUMPTION_SENSORS, # New
    DEFAULT_CREATE_PRODUCTION_SENSORS,  # New
    TOKEN_URL,
    API_GRANT_TYPE,
    API_SCOPE,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EAN): str,
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
        vol.Optional(CONF_DAYS_OFFSET, default=DEFAULT_DAYS_OFFSET): vol.All(vol.Coerce(int), vol.Range(min=0, max=365)), 
        vol.Optional(CONF_MAX_FETCH_DAYS, default=DEFAULT_MAX_FETCH_DAYS): vol.All(vol.Coerce(int), vol.Range(min=1, max=7)),
        vol.Optional(CONF_CREATE_CONSUMPTION_SENSORS, default=DEFAULT_CREATE_CONSUMPTION_SENSORS): bool, # New
        vol.Optional(CONF_CREATE_PRODUCTION_SENSORS, default=DEFAULT_CREATE_PRODUCTION_SENSORS): bool,   # New
    }
)

async def validate_api_credentials(hass, client_id: str, client_secret: str) -> dict:
    """Validate the API credentials by attempting to get a token."""
    _LOGGER.debug("Validating API credentials.")
    session = async_get_clientsession(hass)
    payload = {
        'grant_type': API_GRANT_TYPE,
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': API_SCOPE,
    }
    try:
        async with session.post(TOKEN_URL, data=payload, timeout=10) as response:
            if response.status == 200:
                token_data = await response.json()
                if token_data.get("access_token"):
                    _LOGGER.info("API credentials validated successfully.")
                    return {"status": "ok"}
                _LOGGER.error("API validation failed: Response did not contain access_token. Status: %s, Response: %s", response.status, token_data)
                return {"base": "invalid_auth_token_missing"}
            _LOGGER.error("API validation failed: Invalid credentials or API error. Status: %s, Response: %s", response.status, await response.text())
            return {"base": "invalid_auth"}
    except asyncio.TimeoutError: 
        _LOGGER.error("API validation failed: Timeout connecting to EGD token endpoint.")
        return {"base": "cannot_connect_timeout"}
    except Exception as exc:
        _LOGGER.error(f"API validation failed: An unexpected error occurred: {exc}", exc_info=True)
        return {"base": "unknown"}


class EGDDistribuce24ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EGD-Distribuce24."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the config flow (user-initiated)."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EAN])
            self._abort_if_unique_id_configured()

            validation_result = await validate_api_credentials(
                self.hass, user_input[CONF_CLIENT_ID], user_input[CONF_CLIENT_SECRET]
            )

            if validation_result.get("status") == "ok":
                # Ensure boolean defaults are correctly passed if user unchecks them
                # (user_input might not contain the key if it's unchecked and was default true)
                user_input[CONF_CREATE_CONSUMPTION_SENSORS] = user_input.get(CONF_CREATE_CONSUMPTION_SENSORS, False)
                user_input[CONF_CREATE_PRODUCTION_SENSORS] = user_input.get(CONF_CREATE_PRODUCTION_SENSORS, False)
                
                _LOGGER.info(f"Creating config entry for EAN: {user_input[CONF_EAN]} with sensor selections: Consumption={user_input[CONF_CREATE_CONSUMPTION_SENSORS]}, Production={user_input[CONF_CREATE_PRODUCTION_SENSORS]}")
                return self.async_create_entry(
                    title=f"EGD {user_input[CONF_EAN]}", data=user_input
                )
            else:
                errors = validation_result 

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors,
            description_placeholders={ 
                "days_offset_note": f"Počet dní zpět pro primární cíl dat (např. 2 = předevčerejšek). Výchozí: {DEFAULT_DAYS_OFFSET}.",
                "max_fetch_days_note": f"Maximální počet dalších dní pro zpětné hledání, pokud primární cíl nemá data. Výchozí: {DEFAULT_MAX_FETCH_DAYS}."
            }
        )
