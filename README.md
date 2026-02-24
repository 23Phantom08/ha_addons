# ⚡ Digimeto Customer Portal / 💧 Minol Customer Portal / 🖥️ System Monitoring – Home Assistant Add-on

[![GitHub Release](https://img.shields.io/github/v/release/23Phantom08/ha_addons)](https://github.com/23Phantom08/ha_addons/releases)
[![GitHub Issues](https://img.shields.io/github/issues/23Phantom08/ha_addons)](https://github.com/23Phantom08/ha_addons/issues)
[![Home Assistant Community Add-on](https://img.shields.io/badge/Home%20Assistant-Addon-blue)](https://my.home-assistant.io)

A collection of fully automatic Home Assistant add-ons for integrating **Digimeto Customer Portal**, **Minol Customer Portal**, and **System Monitoring** via MQTT.

---

## 🚀 Quick Start: Direct Installation

Click here to add the add-on repository to Home Assistant:

[![Add repository in Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](
https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https://github.com/23Phantom08/ha_addons)

---

## ✨ Main Features

### ⚡ Digimeto
- 🤖 **Fully automatic login** via Playwright — no manual cookie export!
- 💾 **Persistent session** – Cookies are saved & reused.
- 🔄 **Automatic re-login** on session timeout.
- 📊 **Complete Digimeto history** (day, month, year).
- 🏠 **Home Assistant MQTT Auto-Discovery** integrated.
- 📈 **7-day, 13-month & 3-year history** for optimal Energy Dashboard usage.
- 🧮 **Current year consumption** updated daily

### 💧 Minol

- ✅ Automatic login (Playwright)
- ✅ Heating, hot water, cold water per room
- ✅ **Current & Last billing period sensors**
- ✅ **Automatic hot water correction factor (58.15)**
- ✅ **Zero-value filtering** (only active sensors shown)
- ✅ MQTT Auto-Discovery
- ✅ Customer information sensor

### 🖥️ System Monitoring

- 🖥️ **Real-time CPU usage** – Current processor load (%)
- 💾 **Memory tracking** – RAM usage and availability
- 💿 **Disk storage** – Root filesystem usage monitoring
- 🌐 **Network statistics** – RX/TX bytes, bandwidth monitoring
- 🌡️ **Temperature sensors** – System & component temperatures
- 🔄 **Automatic updates** – Configurable refresh interval (5-60 seconds)
- 📡 **MQTT Auto-Discovery** – Seamless Home Assistant integration
- 🏠 **Background service** – Runs silently, no UI required

---

## 📊 Automatically Created Sensors

**Digimeto**
- Current year consumption (kWh)
- Consumption history (7-day / 13-month / 3-year)

**Minol**
- Heating Total (kWh)
- Hot Water Total (m³)
- Cold Water Total (m³)

**System Monitoring**
- CPU Usage (%)
- Memory Usage (%)
- Disk Usage (%)
- Network RX (bytes)
- Network TX (bytes)
- System Temperature (°C)

---

## 📝 Changelog

### **1.0.0 — 6/02/2026**
- Initial release
- Digimeto: Playwright login integrated
- Minol: Automatic login with zero-value filtering
- System Monitoring: Real-time metrics via MQTT
- MQTT Auto-Discovery support for all add-ons

## 💾 Requirements

- **Home Assistant** 2024.1+
- **MQTT Broker** (mosquitto add-on recommended)
- **Minimum RAM**: 512 MB (for Playwright), 64 MB (System Monitoring)

**Login fails?**
- Check email/password
- Automatic retry after 1-2 min

**Playwright Error?**
- At least 512 MB RAM required

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

**Developed by [23Phantom08](https://github.com/23Phantom08?tab=repositories)**
