# EGD Distribuce24 - Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]][license]
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

Integration for Home Assistant that loads electricity consumption and (optional) production data from the API of the [Distribuce24](https://www.distribuce24.cz/) service, operated by EG.D, a.s. This integration uses the [OpenAPI EG.D](https://data.distribuce24.cz/openapi/egd/namerena-data/latest/).

## Prerequisites

1.  **Account with EG.D Distribuce24**: You must have an active account on the [portal.distribuce24.cz](https://portal.distribuce24.cz/) portal.
2.  **Generated API Keys**: You need to generate a `Client ID` and `Client Secret` in the EG.D customer portal (portal.distribuce24.cz).
    * You can find them in the "Správa účtů" (Account Management) section -> "VZDÁLENÝ PŘÍSTUP - OPENAPI" (REMOTE ACCESS - OPENAPI) tab -> "VYGENEROVAT CLIENT_ID A CLIENT_SECRET" (GENERATE CLIENT_ID AND CLIENT_SECRET) button.
    * These keys are used to obtain an access token, which is valid until midnight of the day it was generated. The integration automatically renews the token.
3.  **Spook Custom Integration**: This integration relies on the `recorder.import_statistics` service, which might be enhanced or modified by the [Spook custom integration](https://github.com/frenck/spook). It is recommended to have Spook installed and updated to ensure compatibility, especially if you encounter issues with statistics import.

## Installation

### Recommended Method: HACS (Home Assistant Community Store)

1.  If you don't have HACS, install it according to the [official guide](https://hacs.xyz/docs/installation/prerequisites).
2.  Open HACS in Home Assistant.
3.  Go to the "Integrations" section.
4.  Click on the three dots in the upper right corner and select "Custom repositories".
5.  In the "Repository" field, paste the URL of your GitHub repository: `https://github.com/zupis/HomeAssistant-EGD-Distribuce24`
6.  Select "Integration" as the "Category".
7.  Click "Add".
8.  Search for "EGD-Distribuce24" in HACS and click "Install".
9.  Follow the instructions and restart Home Assistant.

### Manual Installation

1.  Download the latest [release](https://github.com/zupis/HomeAssistant-EGD-Distribuce24/releases) of your integration from GitHub.
2.  Unzip the archive and copy the `egd_distribuce24` folder (containing files like `manifest.json`, `sensor.py`, etc.) into the `custom_components` folder in your Home Assistant configuration directory. If the `custom_components` folder does not exist, create it.
    * The path should look like: `<config_directory>/custom_components/egd_distribuce24/`.
3.  Restart Home Assistant.

## Configuration

After installation and restarting Home Assistant, you can add the integration via the UI:

1.  Go to "Settings" -> "Devices & Services".
2.  Click the "+ ADD INTEGRATION" button in the bottom right.
3.  Search for "EGD-Distribuce24" and click on it.
4.  Fill out the configuration form:
    * **Metering Point EAN**: Your EAN code (18 digits).
    * **Client ID**: Your Client ID from the EG.D portal.
    * **Client Secret**: Your Client Secret from the EG.D portal.
    * **Days Offset for Data**: Number of days back from the current date for which data should be primarily fetched (e.g., `2` means the day before yesterday). Default: `2`.
    * **Max Fetch Days**: If data is not available for the primary day, the integration will try to fetch data for older days, up to this maximum number of additional days. Default: `3`.
    * **Create consumption sensors**: Check if you want to create sensors for electricity consumption. Default: Enabled.
    * **Create production sensors**: Check if you have electricity production (e.g., photovoltaics) and want to create sensors for grid feed-in. Default: Enabled (if you don't have production, uncheck it).
5.  Click "SUBMIT".

The integration will automatically create the relevant sensors.

## Provided Sensors

The integration can create the following sensors based on your configuration:

* **Active Consumption - Power (kW)**: Current 15-minute average consumption power (profile `ICC1`).
* **Active Consumption - Energy (kWh)**: 15-minute energy consumption (profile `ICQ2`). This sensor is intended for use in the Energy Dashboard.
* **Active Grid Feed-in - Power (kW)**: Current 15-minute average power fed into the grid (profile `ISC1`). Created if production sensor creation is enabled.
* **Active Grid Feed-in - Energy (kWh)**: 15-minute energy fed into the grid (profile `ISQ2`). This sensor is intended for use in the Energy Dashboard (as "Returned to grid"). Created if production sensor creation is enabled.
* **EGD Data Fetch Status**: A sensor that provides information about the last data update attempt and API communication status.

## Energy Dashboard

The energy sensors (`EGDEnergyConsumptionSensor` and `EGDEnergyProductionSensor`) are designed for use with the [Home Assistant Energy Dashboard](https://www.home-assistant.io/docs/energy/).

* After successful data fetching, these sensors should automatically appear in the list of available sensors when configuring the Energy Dashboard.
* The integration imports historical data as **cumulative hourly sums** for the given day to ensure correct display in the dashboard.

**Configuration in Energy Dashboard:**
1.  Go to "Settings" -> "Dashboards" -> "Energy".
2.  In the "Grid consumption" section, add the `EGD Consumption Energy (ICQ2) ...` sensor.
3.  If you have production, in the "Return to grid" section, add the `EGD Production Energy (ISQ2) ...` sensor.

## Sensor Attributes

Energy and power sensors may contain the following attributes:
* `last_update_status`: Status of the last data update attempt.
* `fifteen_minute_data`: List of 15-minute intervals and values from the API for the given day.
* `api_data_points_received`: Number of data points received from the API.
* `data_fetched_for_date_local`: Date (in local Prague time) for which data was successfully fetched.
* `data_range_utc_from`: Start of the data time range in UTC.
* `data_range_utc_to`: End of the data time range in UTC.
* `last_successful_fetch_utc`: Timestamp of the last successful data fetch in UTC.
* `daily_total_kwh` (only on energy sensors with ICQ2/ISQ2 profile): Total consumption/production for the day for which data was fetched (this attribute is for informational purposes; the main sensor state is neutralized for the Energy Dashboard).

## Important Notes on EG.D API

* **Data Update Frequency**: Data for metering points is updated on the EG.D side **once a day in the afternoon**.
* **API Call Limitations**: Frequent repeated API calls load the distributor's system and may lead to temporary blocking of your access. The default synchronization interval in this integration is set to 4 hours (can be changed in `const.py`, but significantly shortening it is not recommended).
* **Token Validity**: The access token is valid until midnight of the day it was generated. The integration handles its automatic renewal.

## Troubleshooting

* If data is not loading or is displayed incorrectly in the Energy Dashboard, check the Home Assistant logs (Settings -> System -> Logs -> Load Full Home Assistant Logs) for messages from the `custom_components.egd_distribuce24` component (especially those prefixed with `[EGD_DISTRIBUCE24_DEBUG]`).
* Verify the correctness of your EAN, Client ID, and Client Secret.
* Ensure you have an active internet connection.
* If you recently changed settings or updated the integration, restart Home Assistant.
* If you have display issues in the Energy Dashboard, try going to "Developer Tools" -> "Statistics", find your sensor (e.g., `sensor.egd_consumption_energy_icq2_...`), and check if any issues are reported there (a "FIX ISSUE" button might appear).
* **Spook Integration**: If you are using the Spook custom integration, be aware that it can modify or enhance core Home Assistant services, including `recorder.import_statistics`. If you encounter unexpected behavior with statistics import, ensure Spook is up to date or temporarily disable it to see if it resolves the issue, helping to isolate the cause.

## Contributing

If you find a bug or have a suggestion for improvement, feel free to create an [Issue](https://github.com/zupis/HomeAssistant-EGD-Distribuce24/issues) on GitHub. Pull requests are also welcome!

## License

This integration is provided under the MIT License. (Please add a `LICENSE` file to your repository).

[releases]: https://github.com/zupis/HomeAssistant-EGD-Distribuce24/releases
[releases-shield]: https://img.shields.io/github/release/zupis/HomeAssistant-EGD-Distribuce24.svg?style=for-the-badge
[license]: https://github.com/zupis/HomeAssistant-EGD-Distribuce24/blob/main/LICENSE
[license-shield]: https://img.shields.io/github/license/zupis/HomeAssistant-EGD-Distribuce24.svg?style=for-the-badge
