# ⚡ Digimeto Customer Portal for Home Assistant

[![License: MIT](https://img.shields.io)](https://opensource.org)
[![Home Assistant Add-on](https://img.shields.io)](https://www.home-assistant.io)

This add-on brings your consumption data from the metering point operator **Digimeto** (Vdis/Robotron Portal) directly into the Home Assistant Energy Dashboard. Thanks to **Playwright automation**, no manual reading of IDs is necessary.

## ⚠️ Important ⚠️

**Please make sure to install both of the following add-ons for it to work**

- Mosquitto broker Add-on
- MQTT Explorer Add-on

## 🚀 Features

- 🔐 **Full Auto-Login**: Takes over SAML login via Chromium (Playwright).
- 🔍 **Dynamic Discovery**: Finds metering point (`mp_id`) and measurement series (`line_id`) automatically.
- 📊 **Real-time Value**: Calculates consumption for the current year.
- 📅 **Comprehensive History**:
  - **7-Day Retrospective**: Individual sensors for the last week.
  - **13-Month Trend**: Perfect for monthly comparison.
  - **3-Year Retrospective**: Perfect for yearly comparison.
- 🆔 **Meter Metadata**: Provides `maloId`, metering point designation and OBIS codes.
- 🏠 **HA Integration**: Complete MQTT Discovery (devices are automatically detected).

## ⚙️ Configuration

**Example for `options` in the add-on**:
(use your own login credentials for Digimeto and MQTT)

```yaml
digimeto_username: "max.mustermann@email.de"
digimeto_password: "your_secure_password"
mqtt_host: "core-mosquitto"
update_interval: 3600
log_level: "info"
```
