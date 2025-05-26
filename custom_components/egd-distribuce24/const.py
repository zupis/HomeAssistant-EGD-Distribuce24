"""Constants for the EGD CZ Power Data integration."""

from datetime import timedelta

# Integration domain
DOMAIN = "egdczpowerdata"

# Configuration keys
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_EAN = "ean"
CONF_DAYS_OFFSET = "days_offset" 
CONF_MAX_FETCH_DAYS = "max_fetch_days"
CONF_CREATE_CONSUMPTION_SENSORS = "create_consumption_sensors" # New
CONF_CREATE_PRODUCTION_SENSORS = "create_production_sensors" # New

# API URLs
TOKEN_URL = "https://idm.distribuce24.cz/oauth/token"
DATA_URL = "https://data.distribuce24.cz/rest/spotreby"

# API Profiles
PROFILE_CONSUMPTION_POWER = "ICC1" 
PROFILE_PRODUCTION_POWER = "ISC1"   
PROFILE_CONSUMPTION_ENERGY = "ICQ2" 
PROFILE_PRODUCTION_ENERGY = "ISQ2"  

# Default values
DEFAULT_DAYS_OFFSET = 2 
DEFAULT_MAX_FETCH_DAYS = 3 
DEFAULT_SCAN_INTERVAL = timedelta(hours=23) 
DEFAULT_CREATE_CONSUMPTION_SENSORS = True # New
DEFAULT_CREATE_PRODUCTION_SENSORS = True  # New

# Attributes used in sensors
ATTR_LAST_UPDATE_STATUS = "last_update_status"
ATTR_FIFTEEN_MINUTE_DATA = "fifteen_minute_data"
ATTR_API_DATA_POINTS_RECEIVED = "api_data_points_received"
ATTR_DATA_FETCHED_FOR_DATE_LOCAL = "data_fetched_for_date_local"
# ... (ostatní atributy zůstávají)
ATTR_DATA_RANGE_UTC_FROM = "data_range_utc_from"
ATTR_DATA_RANGE_UTC_TO = "data_range_utc_to"
ATTR_LAST_SUCCESSFUL_FETCH_UTC = "last_successful_fetch_utc"
ATTR_WATCHED_CONSUMER_SENSOR_ENTITY_ID = "watched_consumer_sensor_entity_id" 
ATTR_CONSUMER_LAST_UPDATE_STATUS = "consumer_last_update_status"
ATTR_CONSUMER_LAST_SUCCESSFUL_FETCH_UTC = "consumer_last_successful_fetch_utc"
ATTR_CONSUMER_DATA_FETCHED_FOR_DATE_LOCAL = "consumer_data_fetched_for_date_local"
ATTR_CONSUMER_TOTAL_KWH = "consumer_total_kwh"
ATTR_LOOKUP_STATUS = "lookup_status"


# Miscellaneous
TIMEZONE_PRAGUE = "Europe/Prague"
API_GRANT_TYPE = "client_credentials"
API_SCOPE = "namerena_data_openapi"
API_PAGE_SIZE = 3000

# Platforms
PLATFORMS = ["sensor"]

