# ⚡ Digimeto Customer Portal / 💧 Minol Customer Portal – Home Assistant Add-on

[![GitHub Release](https://img.shields.io/github/v/release/23Phantom08/ha_addons)](https://github.com/23Phantom08/ha_addons/releases)
[![GitHub Issues](https://img.shields.io/github/issues/23Phantom08/ha_addons)](https://github.com/23Phantom08/ha_addons/issues)
[![Home Assistant Community Add-on](https://img.shields.io/badge/Home%20Assistant-Addon-blue)](https://my.home-assistant.io)

A fully automatic Home Assistant add-on for integrating **Digimeto Customer Portal / Minol Customer Portal
** via MQTT.

---

## 🚀 Quick Start: Direct Installation

Click here to add the add-on repository to Home Assistant:

[![Add repository in Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](
https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https://github.com/23Phantom08/ha_addons)

---

## ✨ Main Features

- 🤖 **Fully automatic login** via Playwright — no manual cookie export!
- 💾 **Persistent session** – Cookies are saved & reused.
- 🔄 **Automatic re-login** on session timeout.
- 📊 **Complete Digimeto history** (day, month, year).
- 🏠 **Home Assistant MQTT Auto-Discovery** integrated.
- 📈 **7-day, 13-month & 3-year history** for optimal Energy Dashboard usage.
- 🧮 **Current year consumption** updated daily

---

## 📊 Automatically Created Sensors

**Digimeto**
- Current year consumption (kWh)
- Consumption history (7-day / 13-month / 3-year)

**Minol**
- Heating Total (kWh)
- Hot Water Total (m³)
- Cold Water Total (m³)

---

## 📝 Changelog

### **1.0.0 — 6/02/2026**
- Initial release
- Playwright login integrated
- MQTT Auto-Discovery support

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
