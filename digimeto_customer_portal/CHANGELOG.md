# Changelog - Digimeto Customer Portal

## [1.2.0] - 2026-03-15

### 🐛 Bug Fixes
- Fixed month sensor names showing wrong labels (e.g. double "Dezember", "Januar" instead of "Februar")
  - Root cause: `timedelta(days=i*30)` drifted incorrectly across short months like February
  - Replaced with reliable modulo arithmetic directly on month/year values

---

## [1.1.0] - 2026-02-10

### 🔧 Improvements
- **HA 2026.4 Compatibility**: Fixed deprecated MQTT discovery configuration
  - Replaced `object_id` with `default_entity_id` 
  - Changed `state_class: measurement` to `total` for energy sensors
  - No more warnings in Home Assistant logs

### 🐛 Bug Fixes
- Fixed MQTT sensor discovery warnings
- Fixed entity ID configuration for all sensors (days, months, years)
- Improved energy sensor state class configuration

### ⚠️ Breaking Changes
**None** - This release is fully backward compatible. All existing entities continue to work.

---

## [1.0.0] - 2026-02-05

### 🎉 Initial Release
- Automatic Playwright login with SAML authentication
- MQTT Auto-Discovery integration
- Daily consumption tracking (7 days)
- Monthly consumption history (13 months)
- Yearly consumption (last 3 years)
- Dynamic sensor naming with date/year information
