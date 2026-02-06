# 📊 Digimeto Home Assistant Add-on

This add-on integrates electricity data from the **Digimeto Customer Portal** via MQTT into Home Assistant. It uses Playwright for automated login and provides historical data (days, months, years).

## ✨ Features
- 🔐 **Fully automatic login** via Playwright (SAML support).
- 📡 **MQTT Auto-Discovery**: Sensors are automatically created in Home Assistant.
- 🧮 **Current year**: summed daily with the carry-over value (Digimeto does not yet provide values for the current day)
- 📅 **Historical data**: 7 days, 13 months and 3 years history.
- 🛠️ **Easy configuration**: Directly through the Home Assistant user interface.

## ⚙️ Configuration
The following options must be set:
- `digimeto_username`: Your login for the portal.
- `digimeto_password`: Your password.
- `mqtt_host`: Usually `core-mosquitto`.
- `update_interval`: Time in seconds between retrievals (Recommended: `3600` for 1h).

## 📊 Dashboard Template (Example)

Copy this YAML code into a **Manual Card** in your dashboard to get a clean overview:

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-title-card
    title: 📊 Digimeto Meter
    subtitle: Consumption Overview
    alignment: start
  - type: entities
    title: 🔧 Basic Data
    entities:
      - entity: sensor.digimeto_mq
        name: Meter OBIS Code
        icon: mdi:barcode-scan
      - entity: sensor.digimeto_maloid
        name: Market Location ID
        icon: mdi:identifier
      - entity: sensor.digimeto_metpoint
        name: Metering Point Designation
        icon: mdi:map-marker
  - type: custom:mushroom-title-card
    title: 📅 Daily Consumption
    alignment: start
  - type: entities
    entities:
      - entity: sensor.digimeto_day_1
      - entity: sensor.digimeto_day_2
      - entity: sensor.digimeto_day_3
      - entity: sensor.digimeto_day_4
      - entity: sensor.digimeto_day_5
      - entity: sensor.digimeto_day_6
      - entity: sensor.digimeto_day_7
  - type: custom:mushroom-title-card
    title: 🗓️ Monthly Consumption
    alignment: start
  - type: entities
    entities:
      - entity: sensor.digimeto_mon_1
      - entity: sensor.digimeto_mon_2
      - entity: sensor.digimeto_mon_3
      - entity: sensor.digimeto_mon_4
      - entity: sensor.digimeto_mon_5
      - entity: sensor.digimeto_mon_6
      - entity: sensor.digimeto_mon_7
      - entity: sensor.digimeto_mon_8
      - entity: sensor.digimeto_mon_9
      - entity: sensor.digimeto_mon_10
      - entity: sensor.digimeto_mon_11
      - entity: sensor.digimeto_mon_12
      - entity: sensor.digimeto_mon_13
  - type: custom:mushroom-title-card
    title: 📆 Yearly Consumption
    alignment: start
  - type: entities
    entities:
      - entity: sensor.digimeto_current_year
      - entity: sensor.digimeto_year_1
      - entity: sensor.digimeto_year_2
```
