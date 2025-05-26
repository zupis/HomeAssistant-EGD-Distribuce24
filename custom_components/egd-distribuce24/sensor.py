import logging
import requests
import datetime 
from datetime import timedelta
from datetime import datetime as dt_module 
import voluptuous as vol 
from dateutil import tz as dateutil_tz 
import os 
from homeassistant import config_entries 

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity, 
)
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.util import Throttle 
from homeassistant.util import dt as dt_util 
from homeassistant.helpers import entity_registry as er
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback 

from .const import (
    DOMAIN,
    TOKEN_URL,
    DATA_URL,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_EAN,
    CONF_DAYS_OFFSET,
    CONF_MAX_FETCH_DAYS, 
    CONF_CREATE_CONSUMPTION_SENSORS, # New
    CONF_CREATE_PRODUCTION_SENSORS,  # New
    PROFILE_CONSUMPTION_POWER, 
    PROFILE_PRODUCTION_POWER,  
    PROFILE_CONSUMPTION_ENERGY, 
    PROFILE_PRODUCTION_ENERGY,  
    DEFAULT_SCAN_INTERVAL, 
    TIMEZONE_PRAGUE,
    API_GRANT_TYPE,
    API_SCOPE,
    API_PAGE_SIZE,
    ATTR_LAST_UPDATE_STATUS,
    ATTR_FIFTEEN_MINUTE_DATA,
    ATTR_API_DATA_POINTS_RECEIVED,
    ATTR_DATA_FETCHED_FOR_DATE_LOCAL,
    ATTR_DATA_RANGE_UTC_FROM,
    ATTR_DATA_RANGE_UTC_TO,
    ATTR_LAST_SUCCESSFUL_FETCH_UTC,
    ATTR_WATCHED_CONSUMER_SENSOR_ENTITY_ID,
    ATTR_CONSUMER_LAST_UPDATE_STATUS,
    ATTR_CONSUMER_LAST_SUCCESSFUL_FETCH_UTC,
    ATTR_CONSUMER_DATA_FETCHED_FOR_DATE_LOCAL,
    ATTR_CONSUMER_TOTAL_KWH,
    ATTR_LOOKUP_STATUS,
    PLATFORMS, 
)

MIN_TIME_BETWEEN_UPDATES = DEFAULT_SCAN_INTERVAL
SCRIPT_VERSION = "1.0.14_sensor_selection" # Version marker

_LOGGER = logging.getLogger(__name__)

LOG_DIR = "/config/logs/egdczpowerdata" 
LOG_FILE = os.path.join(LOG_DIR, f"{DOMAIN}.log")

try:
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    file_handler = logging.FileHandler(LOG_FILE, mode='a')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == LOG_FILE for h in _LOGGER.handlers):
        _LOGGER.addHandler(file_handler)
    _LOGGER.info(f"--- DEDICATED LOGGER FOR {DOMAIN} INITIALIZED. Logging to: {LOG_FILE} --- Version: {SCRIPT_VERSION} ---")

except Exception as e_log_setup:
    _LOGGER.error(f"Error setting up dedicated file logger for {DOMAIN}: {e_log_setup}. Falling back to standard HA logging.", exc_info=True)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry, 
    async_add_entities: AddEntitiesCallback, 
) -> None:
    """Set up EGD CZ Power Data sensors from a config entry."""
    _LOGGER.info(f"Setting up sensors for EGD CZ Power Data config entry: {config_entry.title} (Script Version: {SCRIPT_VERSION})")

    entry_data = config_entry.data
    client_id = entry_data[CONF_CLIENT_ID]
    client_secret = entry_data[CONF_CLIENT_SECRET]
    ean = entry_data[CONF_EAN]
    days_offset = entry_data[CONF_DAYS_OFFSET]
    max_fetch_days = entry_data[CONF_MAX_FETCH_DAYS]
    create_consumption = entry_data.get(CONF_CREATE_CONSUMPTION_SENSORS, True) # Default to True if key missing
    create_production = entry_data.get(CONF_CREATE_PRODUCTION_SENSORS, True)   # Default to True if key missing
    
    _LOGGER.info(f"Config for EAN {ean}: DaysOffset={days_offset}, MaxFetch={max_fetch_days}, CreateConsumption={create_consumption}, CreateProduction={create_production}")

    if DOMAIN not in hass.data: 
        hass.data[DOMAIN] = {}
    if 'entries' not in hass.data[DOMAIN]:
        hass.data[DOMAIN]['entries'] = {}
    hass.data[DOMAIN]['entries'][ean] = {
        "entry_id": config_entry.entry_id,
        "client_id": client_id, 
        "client_secret": client_secret 
    }

    sensors_to_add = []
    consumption_power_sensor = None # Initialize to None

    try:
        if create_consumption:
            consumption_power_sensor = EGDPowerConsumptionSensor(hass, client_id, client_secret, ean, days_offset, max_fetch_days, config_entry.entry_id)
            sensors_to_add.append(consumption_power_sensor)
            consumption_energy_sensor = EGDEnergyConsumptionSensor(hass, client_id, client_secret, ean, days_offset, max_fetch_days, config_entry.entry_id)
            sensors_to_add.append(consumption_energy_sensor)
            _LOGGER.info(f"Consumption sensors scheduled for addition for EAN {ean}.")

        if create_production:
            production_power_sensor = EGDPowerProductionSensor(hass, client_id, client_secret, ean, days_offset, max_fetch_days, config_entry.entry_id)
            sensors_to_add.append(production_power_sensor)
            production_energy_sensor = EGDEnergyProductionSensor(hass, client_id, client_secret, ean, days_offset, max_fetch_days, config_entry.entry_id)
            sensors_to_add.append(production_energy_sensor)
            _LOGGER.info(f"Production sensors scheduled for addition for EAN {ean}.")
        
        # Add status sensor only if consumption sensors are being created (as it watches one of them)
        if consumption_power_sensor: # Check if the primary consumption sensor was created
            status_sensor = EGDStatusSensor(hass, ean, days_offset, consumption_power_sensor.unique_id, config_entry.entry_id) 
            sensors_to_add.append(status_sensor)
            _LOGGER.info(f"Status sensor scheduled for addition for EAN {ean}.")
        elif not create_consumption and create_production:
             _LOGGER.warning(f"Status sensor not added for EAN {ean} as consumption sensors are disabled, but production sensors are enabled. Status sensor typically watches consumption.")
        elif not create_consumption and not create_production:
            _LOGGER.info(f"No data or status sensors will be added for EAN {ean} as both consumption and production are disabled.")


        if sensors_to_add:
            _LOGGER.debug(f"Sensors created and ready to be added for EAN {ean}:")
            for sensor in sensors_to_add:
                _LOGGER.debug(f" - Sensor: {sensor.name}, Unique ID: {sensor.unique_id}, Object: {sensor}")
            async_add_entities(sensors_to_add, True) 
            _LOGGER.info(f"Sensor entities for EAN {ean} (entry: {config_entry.title}) have been processed for addition.")
        else:
            _LOGGER.info(f"No sensors were configured for addition for EAN {ean}.")


    except Exception as e:
        _LOGGER.error(f"Error during sensor instantiation or add_entities for EAN {ean}: {e}", exc_info=True)

class EGDBaseSensor(SensorEntity):
    """Base class for EGD data sensors."""

    _attr_device_class = SensorDeviceClass.ENERGY 

    def __init__(self, hass: HomeAssistant, client_id: str, client_secret: str, ean: str, 
                 days_offset: int, max_fetch_days: int, api_profile: str, 
                 profile_friendly_name: str, entry_id: str, 
                 is_value_direct_kwh: bool = False,
                 target_unit: str = UnitOfEnergy.KILO_WATT_HOUR, 
                 target_state_class: SensorStateClass = SensorStateClass.TOTAL): 
        self.hass = hass
        self._client_id = client_id
        self._client_secret = client_secret
        self._ean = str(ean) 
        self._days_offset = days_offset 
        self._max_fetch_days = max_fetch_days 
        self._api_profile = api_profile
        self._profile_friendly_name = profile_friendly_name 
        self._entry_id = entry_id 
        self._is_value_direct_kwh = is_value_direct_kwh
        self._target_unit = target_unit
        self._target_state_class = target_state_class
        
        self._session = requests.Session()
        self._state: float | None = None 
        self._attributes: dict[str, any] = {}
        self._last_reset_datetime_utc: dt_module | None = None 

        self._attr_unique_id = f"{DOMAIN}_{self._ean}_{self._days_offset}_{self._api_profile.lower()}"
        
        day_desc_en = f"{self._days_offset}d ago (win {self._max_fetch_days}d)" 
        
        self._attr_name = f"EGD {self._profile_friendly_name} {self._ean} ({day_desc_en})"
        _LOGGER.info(f"Initialized EGDBaseSensor (v{SCRIPT_VERSION}): {self.name}, Unique ID: {self.unique_id}, Direct kWh flag: {self._is_value_direct_kwh}, Target Unit: {self._target_unit}, Target State Class: {self._target_state_class}")

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the class of this device."""
        if self._target_unit == UnitOfEnergy.KILO_WATT_HOUR:
            return SensorDeviceClass.ENERGY
        elif self._target_unit == UnitOfPower.KILO_WATT:
            return SensorDeviceClass.POWER
        return None

    @property
    def unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of this entity."""
        return self._target_unit

    @property
    def state_class(self) -> SensorStateClass | None:
        """Return the state class of this entity."""
        return self._target_state_class

    @property
    def device_info(self):
        try:
            return {
                "identifiers": {(DOMAIN, str(self._ean))}, 
                "name": f"EGD Device ({str(self._ean)})", 
                "manufacturer": "EGD CZ", 
            }
        except Exception as e:
            _LOGGER.error(f"Error generating device_info for {self.name}: {e}", exc_info=True)
            return None 

    @property
    def state(self) -> float | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        return self._attributes

    @property
    def last_reset(self) -> dt_module | None: 
        if self._target_state_class == SensorStateClass.TOTAL or self._target_state_class == SensorStateClass.TOTAL_INCREASING:
            return self._last_reset_datetime_utc
        return None

    @Throttle(MIN_TIME_BETWEEN_UPDATES) 
    async def async_update(self) -> None: 
        _LOGGER.debug(f"Throttled 'async_update' called for '{self.name}'. Triggering _perform_update.")
        await self.hass.async_add_executor_job(self._perform_update)

    def _perform_update(self) -> None:
        """Iteratively try to fetch data for past days if recent data is unavailable."""
        _LOGGER.info(f"Executing _perform_update for '{self.name}'. Primary offset: {self._days_offset}, Max fetch window: {self._max_fetch_days} days.")

        access_token = self._get_access_token_from_api()
        if not access_token:
            self._attributes[ATTR_LAST_UPDATE_STATUS] = 'Token Retrieval Failed'
            self._state = None 
            if self._target_state_class == SensorStateClass.TOTAL:
                try:
                    local_tz = dateutil_tz.gettz(TIMEZONE_PRAGUE) or dt_util.now().tzinfo
                    now_in_local_tz = dt_util.now(local_tz)
                    primary_target_date_local = now_in_local_tz - timedelta(days=self._days_offset)
                    self._last_reset_datetime_utc = primary_target_date_local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(dateutil_tz.tzutc())
                except Exception: 
                    self._last_reset_datetime_utc = None 
            return

        data_found_for_any_day = False
        
        for i in range(self._max_fetch_days):
            current_days_offset = self._days_offset + i
            _LOGGER.info(f"Attempting fetch for day offset: {current_days_offset} (Attempt {i+1}/{self._max_fetch_days}) for '{self.name}'")

            try:
                local_tz = dateutil_tz.gettz(TIMEZONE_PRAGUE)
                if not local_tz:
                    _LOGGER.warning(f"Timezone '{TIMEZONE_PRAGUE}' not found, using system's local timezone.")
                    local_tz = dt_util.now().tzinfo 
                
                now_in_local_tz = dt_util.now(local_tz)
                target_date_local = now_in_local_tz - timedelta(days=current_days_offset)
                
                period_start_local = target_date_local.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end_local = target_date_local.replace(hour=23, minute=45, second=0, microsecond=0)

            except Exception as e_time:
                _LOGGER.error(f"Error calculating time period for offset {current_days_offset} for '{self.name}': {e_time}", exc_info=True)
                continue 
            
            processed_data = self._fetch_and_process_data_for_day(access_token, period_start_local, period_end_local, target_date_local)
            
            if processed_data["data_found"]:
                if self._target_state_class == SensorStateClass.TOTAL: 
                    self._state = processed_data["total_kwh_for_day"]
                    self._last_reset_datetime_utc = period_start_local.astimezone(dateutil_tz.tzutc())
                elif self._target_state_class == SensorStateClass.MEASUREMENT: 
                    if processed_data["detailed_intervals"]:
                        # For power sensors (kW), set state to the value of the last interval
                        # The 'value' in detailed_intervals is the raw value from API (kW for power profiles)
                        self._state = processed_data["detailed_intervals"][-1].get('value') 
                    else:
                        self._state = None 
                
                self._attributes.update(processed_data["attributes_to_set"])
                _LOGGER.info(f"Data successfully fetched and processed for '{self.name}' for date {target_date_local.strftime('%Y-%m-%d')}. State: {self._state} {self.unit_of_measurement}")
                data_found_for_any_day = True
                break 
            else:
                _LOGGER.info(f"No data found for '{self.name}' for date {target_date_local.strftime('%Y-%m-%d')}. Trying next older day if within window.")
                self._attributes[ATTR_LAST_UPDATE_STATUS] = processed_data["attributes_to_set"].get(ATTR_LAST_UPDATE_STATUS, "Fetch Failed")


        if not data_found_for_any_day:
            _LOGGER.warning(f"No data found for '{self.name}' within the {self._max_fetch_days}-day fetch window (primary offset {self._days_offset}).")
            if self._target_state_class == SensorStateClass.TOTAL: 
                self._state = 0.0
            else: 
                self._state = None 
            self._attributes[ATTR_LAST_UPDATE_STATUS] = f'No data in {self._max_fetch_days}-day window'
            self._attributes[ATTR_FIFTEEN_MINUTE_DATA] = []
            self._attributes[ATTR_API_DATA_POINTS_RECEIVED] = 0
            if self._target_state_class == SensorStateClass.TOTAL:
                try:
                    local_tz = dateutil_tz.gettz(TIMEZONE_PRAGUE) or dt_util.now().tzinfo
                    now_in_local_tz = dt_util.now(local_tz)
                    primary_target_date_local = now_in_local_tz - timedelta(days=self._days_offset)
                    self._last_reset_datetime_utc = primary_target_date_local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(dateutil_tz.tzutc())
                    self._attributes[ATTR_DATA_FETCHED_FOR_DATE_LOCAL] = "N/A (No data in window)"
                except Exception: 
                     self._last_reset_datetime_utc = None 
                     self._attributes[ATTR_DATA_FETCHED_FOR_DATE_LOCAL] = "N/A (Timezone error)"
            else:
                self._last_reset_datetime_utc = None 
                self._attributes[ATTR_DATA_FETCHED_FOR_DATE_LOCAL] = "N/A (No data in window)"

        
    def _get_access_token_from_api(self) -> str | None:
        """Retrieve access token from EGD API (synchronous)."""
        _LOGGER.info(f"Requesting access token for '{self.name}' (EAN: {self._ean})")
        try:
            response = self._session.post(
                TOKEN_URL,
                data={
                    'grant_type': API_GRANT_TYPE,
                    'client_id': self._client_id,
                    'client_secret': self._client_secret,
                    'scope': API_SCOPE
                },
                timeout=20 
            )
            _LOGGER.debug(f"Token API response status for '{self.name}': {response.status_code}")
            response.raise_for_status()
            token_data = response.json()
            token = token_data.get('access_token')
            if token:
                _LOGGER.info(f"Access token successfully retrieved for '{self.name}'.")
                return token
            else:
                _LOGGER.error(f"Access token not found in API response for '{self.name}'. Response: {token_data}")
                return None
        except requests.exceptions.HTTPError as e:
            _LOGGER.error(f"HTTP error retrieving access token for '{self.name}': {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Network error retrieving access token for '{self.name}': {e}")
        except ValueError as e: 
            _LOGGER.error(f"JSON decode error retrieving access token for '{self.name}': {e}")
        return None

    def _fetch_and_process_data_for_day(self, token: str, period_start_local: dt_module, period_end_local: dt_module, target_date_local_for_log: dt_module) -> dict:
        """Fetch data from EGD API for a specific day and process it. 
           Returns a dictionary with 'data_found' (bool), 'attributes_to_set' (dict), 
           'total_kwh_for_day' (float), and 'detailed_intervals' (list).
        """
        
        from_utc = period_start_local.astimezone(dateutil_tz.tzutc())
        to_utc = period_end_local.astimezone(dateutil_tz.tzutc())

        api_params = {
            'ean': self._ean,
            'profile': self._api_profile,
            'from': from_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'to': to_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'pageSize': API_PAGE_SIZE 
        }
        _LOGGER.info(f"Fetching data for '{self.name}' for specific date {target_date_local_for_log.strftime('%Y-%m-%d')} (Profile: {self._api_profile})")
        _LOGGER.debug(f"API Request Params for specific day: {api_params}")

        result = {
            "data_found": False,
            "total_kwh_for_day": 0.0,
            "detailed_intervals": [],
            "attributes_to_set": {}
        }

        try:
            response = self._session.get(DATA_URL, headers={'Authorization': f'Bearer {token}'}, params=api_params, timeout=30)
            _LOGGER.debug(f"Data API response status for '{self.name}' (date: {target_date_local_for_log.strftime('%Y-%m-%d')}): {response.status_code}")
            response.raise_for_status()
            api_response_data = response.json()
            _LOGGER.debug(f"Data API raw response for '{self.name}' (date: {target_date_local_for_log.strftime('%Y-%m-%d')}): {str(api_response_data)[:500]}...")

            detailed_intervals_temp = []
            total_kwh_for_day_temp = 0.0
            
            if api_response_data and isinstance(api_response_data, list) and len(api_response_data) > 0 and \
               'data' in api_response_data[0] and isinstance(api_response_data[0]['data'], list) and \
               len(api_response_data[0]['data']) > 0: 
                
                raw_intervals_data = api_response_data[0]['data']
                api_units = api_response_data[0].get("units", "KW").upper() 
                _LOGGER.info(f"Received {len(raw_intervals_data)} raw interval(s) from API for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}. API reports units: {api_units}")

                for item in raw_intervals_data:
                    timestamp_str = item.get('timestamp')
                    value_from_api = item.get('value') 
                    status_code = item.get('status')

                    if isinstance(value_from_api, (int, float)) and timestamp_str:
                        value_kwh_interval: float
                        if self._is_value_direct_kwh: 
                            value_kwh_interval = float(value_from_api)
                        else: 
                            value_kwh_interval = float(value_from_api) / 4.0
                        
                        total_kwh_for_day_temp += value_kwh_interval
                        detailed_intervals_temp.append({
                            'timestamp_utc': timestamp_str,
                            'value': round(float(value_from_api), 3), 
                            'unit_of_value': api_units, 
                            'status': status_code
                        })
                    else:
                        _LOGGER.warning(f"Skipping invalid interval item: {item} for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}")
                
                if detailed_intervals_temp: 
                    result["data_found"] = True
                    result["total_kwh_for_day"] = round(total_kwh_for_day_temp, 3)
                    result["detailed_intervals"] = detailed_intervals_temp # This will be used by power sensors for the last value
                    result["attributes_to_set"] = {
                        ATTR_LAST_UPDATE_STATUS: 'Success',
                        ATTR_FIFTEEN_MINUTE_DATA: detailed_intervals_temp, # Store all intervals
                        ATTR_API_DATA_POINTS_RECEIVED: len(detailed_intervals_temp),
                        ATTR_DATA_FETCHED_FOR_DATE_LOCAL: target_date_local_for_log.strftime('%Y-%m-%d'),
                        ATTR_DATA_RANGE_UTC_FROM: from_utc.isoformat(),
                        ATTR_DATA_RANGE_UTC_TO: to_utc.isoformat(),
                        ATTR_LAST_SUCCESSFUL_FETCH_UTC: dt_util.utcnow().isoformat()
                    }
                    _LOGGER.info(f"Data processed for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}. Total kWh for day (if applicable): {result['total_kwh_for_day']}")
                elif not detailed_intervals_temp and raw_intervals_data: 
                    _LOGGER.warning(f"No valid intervals processed from API data for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}, though raw data was present.")
                    result["attributes_to_set"][ATTR_LAST_UPDATE_STATUS] = 'No valid intervals in data'
            
            elif api_response_data and 'error' in api_response_data and api_response_data['error'] == 'No results':
                _LOGGER.info(f"API returned 'No results' for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}.")
                result["attributes_to_set"][ATTR_LAST_UPDATE_STATUS] = 'Success (No results from API)'
            
            elif api_response_data and isinstance(api_response_data, list) and len(api_response_data) > 0 and \
                 'data' in api_response_data[0] and isinstance(api_response_data[0]['data'], list) and \
                 len(api_response_data[0]['data']) == 0: 
                _LOGGER.info(f"API returned an empty 'data' list for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}.")
                result["attributes_to_set"][ATTR_LAST_UPDATE_STATUS] = 'Success (No data points)'
            else: 
                _LOGGER.warning(f"Unexpected API response format or no data for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}. Response: {str(api_response_data)[:500]}")
                result["attributes_to_set"][ATTR_LAST_UPDATE_STATUS] = 'Unexpected API response'

        except requests.exceptions.HTTPError as e:
            _LOGGER.error(f"API HTTP error fetching data for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}: {e.response.status_code} - {e.response.text}")
            result["attributes_to_set"][ATTR_LAST_UPDATE_STATUS] = f'API HTTP Error {e.response.status_code}'
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"API network error fetching data for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}: {e}")
            result["attributes_to_set"][ATTR_LAST_UPDATE_STATUS] = 'API Network Error'
        except ValueError as e: 
            _LOGGER.error(f"API JSON decode error for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}': {e}. Response text: {response.text if 'response' in locals() and response else 'N/A'}")
            result["attributes_to_set"][ATTR_LAST_UPDATE_STATUS] = 'API JSON Decode Error'
        except Exception as e: 
            _LOGGER.error(f"Generic error processing data for '{self.name}' for date {target_date_local_for_log.strftime('%Y-%m-%d')}: {e}", exc_info=True)
            result["attributes_to_set"][ATTR_LAST_UPDATE_STATUS] = 'Data Processing Error'
        
        if not result["data_found"] and ATTR_LAST_UPDATE_STATUS not in result["attributes_to_set"] :
             result["attributes_to_set"][ATTR_LAST_UPDATE_STATUS] = f'Failed fetch for {target_date_local_for_log.strftime("%Y-%m-%d")}'
        return result


class EGDPowerConsumptionSensor(EGDBaseSensor): 
    """Sensor for EGD power consumption (ICC1 - kW)."""
    def __init__(self, hass: HomeAssistant, client_id: str, client_secret: str, ean: str, days_offset: int, max_fetch_days: int, entry_id: str):
        super().__init__(hass, client_id, client_secret, ean, days_offset, max_fetch_days, 
                         PROFILE_CONSUMPTION_POWER, f"Consumption Power ({PROFILE_CONSUMPTION_POWER})", entry_id, 
                         is_value_direct_kwh=False,
                         target_unit=UnitOfPower.KILO_WATT, 
                         target_state_class=SensorStateClass.MEASUREMENT) 

class EGDPowerProductionSensor(EGDBaseSensor): 
    """Sensor for EGD power production (ISC1 - kW)."""
    def __init__(self, hass: HomeAssistant, client_id: str, client_secret: str, ean: str, days_offset: int, max_fetch_days: int, entry_id: str):
        super().__init__(hass, client_id, client_secret, ean, days_offset, max_fetch_days, 
                         PROFILE_PRODUCTION_POWER, f"Production Power ({PROFILE_PRODUCTION_POWER})", entry_id,
                         is_value_direct_kwh=False,
                         target_unit=UnitOfPower.KILO_WATT, 
                         target_state_class=SensorStateClass.MEASUREMENT) 

class EGDEnergyConsumptionSensor(EGDBaseSensor): 
    """Sensor for EGD energy consumption (ICQ2 - kWh)."""
    def __init__(self, hass: HomeAssistant, client_id: str, client_secret: str, ean: str, days_offset: int, max_fetch_days: int, entry_id: str):
        super().__init__(hass, client_id, client_secret, ean, days_offset, max_fetch_days, 
                         PROFILE_CONSUMPTION_ENERGY, f"Consumption Energy ({PROFILE_CONSUMPTION_ENERGY})", entry_id,
                         is_value_direct_kwh=True,
                         target_unit=UnitOfEnergy.KILO_WATT_HOUR, 
                         target_state_class=SensorStateClass.TOTAL) 

class EGDEnergyProductionSensor(EGDBaseSensor): 
    """Sensor for EGD energy production (ISQ2 - kWh)."""
    def __init__(self, hass: HomeAssistant, client_id: str, client_secret: str, ean: str, days_offset: int, max_fetch_days: int, entry_id: str):
        super().__init__(hass, client_id, client_secret, ean, days_offset, max_fetch_days, 
                         PROFILE_PRODUCTION_ENERGY, f"Production Energy ({PROFILE_PRODUCTION_ENERGY})", entry_id,
                         is_value_direct_kwh=True,
                         target_unit=UnitOfEnergy.KILO_WATT_HOUR, 
                         target_state_class=SensorStateClass.TOTAL) 


class EGDStatusSensor(SensorEntity):
    """Sensor to reflect the status of EGD data retrieval."""

    def __init__(self, hass: HomeAssistant, ean: str, days_offset_config: int, consumption_sensor_unique_id: str, entry_id: str): 
        self.hass = hass
        self._ean = str(ean) 
        self._days_offset_config = days_offset_config 
        self._consumption_sensor_unique_id = consumption_sensor_unique_id 
        self._entry_id = entry_id
        
        self._attr_name = f"EGD Data Status {self._ean} (offset {self._days_offset_config}d)"
        self._attr_unique_id = f"{DOMAIN}_status_{self._ean}_{self._days_offset_config}" 
        self._state: str | None = "Initializing"
        self._attributes: dict[str, any] = {}
        _LOGGER.info(f"--- EGDStatusSensor __init__ CALLED (v{SCRIPT_VERSION}): {self.name}, watching {self._consumption_sensor_unique_id} ---")

    @property
    def device_info(self):
        try:
            return {
                "identifiers": {(DOMAIN, str(self._ean))}, 
                "name": f"EGD Device ({str(self._ean)})", 
                "manufacturer": "EGD CZ",
            }
        except Exception as e:
            _LOGGER.error(f"Error generating device_info for {self.name}: {e}", exc_info=True)
            return None


    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        return self._attributes
    
    @property
    def icon(self) -> str:
        current_state_lower = str(self.state).lower() if self.state else "unknown"
        if "success" in current_state_lower or "ok" in current_state_lower : 
            return "mdi:check-circle-outline"
        elif "error" in current_state_lower or "failed" in current_state_lower or "not_found" in current_state_lower or "not_registered" in current_state_lower:
            return "mdi:alert-circle-outline"
        return "mdi:timer-sand" 

    async def async_update(self) -> None: 
        _LOGGER.debug(f"Updating EGDStatusSensor for '{self.name}'")

        entity_reg = er.async_get(self.hass)
        consumption_entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, self._consumption_sensor_unique_id)
        
        if not consumption_entity_id:
            _LOGGER.warning(f"StatusSensor: Consumption sensor with unique_id '{self._consumption_sensor_unique_id}' not found in entity registry.")
            self._state = "Error: Main sensor not registered"
            self._attributes[ATTR_LOOKUP_STATUS] = f"Consumption sensor unique_id '{self._consumption_sensor_unique_id}' not in registry."
            return

        consumption_state_obj = self.hass.states.get(consumption_entity_id)
        if not consumption_state_obj:
            _LOGGER.warning(f"StatusSensor: State object for consumption sensor '{consumption_entity_id}' (unique_id: {self._consumption_sensor_unique_id}) not found. May be initializing.")
            self._state = "Pending: Main sensor state unavailable"
            self._attributes[ATTR_LOOKUP_STATUS] = f"State for '{consumption_entity_id}' unavailable."
            return

        self._attributes[ATTR_WATCHED_CONSUMER_SENSOR_ENTITY_ID] = consumption_entity_id
        last_status = consumption_state_obj.attributes.get(ATTR_LAST_UPDATE_STATUS, 'N/A')
        self._attributes[ATTR_CONSUMER_LAST_UPDATE_STATUS] = last_status
        self._attributes[ATTR_CONSUMER_LAST_SUCCESSFUL_FETCH_UTC] = consumption_state_obj.attributes.get(ATTR_LAST_SUCCESSFUL_FETCH_UTC)
        self._attributes[ATTR_CONSUMER_DATA_FETCHED_FOR_DATE_LOCAL] = consumption_state_obj.attributes.get(ATTR_DATA_FETCHED_FOR_DATE_LOCAL)
        self._attributes["watched_sensor_state"] = consumption_state_obj.state 
        self._attributes["watched_sensor_unit"] = consumption_state_obj.attributes.get("unit_of_measurement")


        if str(last_status).startswith('Success'): 
            self._state = f"OK ({last_status})"
        elif last_status == 'N/A': 
            self._state = "Pending first data"
        else: 
            self._state = f"Error ({last_status})"
        
        _LOGGER.debug(f"StatusSensor '{self.name}' updated. State: {self.state}, Consumer Last Status: {last_status}")

