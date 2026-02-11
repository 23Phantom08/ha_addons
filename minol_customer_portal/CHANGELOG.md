# Changelog - Minol Customer Portal

## [1.1.0] - 2026-02-10

### ✨ New Features
- **Billing Period Sensors**: Current and last billing period consumption tracking
  - `sensor.minol_heating_period_current` - Current billing period (e.g., Sep 2025 - Feb 2026)
  - `sensor.minol_heating_period_last` - Previous full billing period (e.g., Sep 2024 - Aug 2025)
  - Available for heating, hot water, and cold water
- **Hot Water Correction Factor**: Automatic correction (÷58.15) for hot water billing period sensors
- **Zero-Value Filtering**: Room sensors with 0 consumption are no longer created (cleaner UI)
- **Customer Info Sensor**: New sensor with customer number, address, tenant info, move-in date
- **Configurable Billing Period**: Set your billing start month in config (1-12)

### 🔧 Improvements
- Replaced deprecated `object_id` with `default_entity_id` (HA 2026.4 compatibility)
- Fixed `state_class` for energy sensors (`measurement` → `total`)
- Improved logging output with clearer messages
- Better error handling and session management

### 📋 Configuration Changes
**New required setting:**
```yaml
billing_start_month: 9  # Your billing period start month (1-12)
```

**Example configurations:**
- September billing: `billing_start_month: 9` (default)
- March billing: `billing_start_month: 3`
- January billing: `billing_start_month: 1`

### 🐛 Bug Fixes
- Fixed hot water values showing incorrect raw API data
- Fixed Home Assistant warnings about deprecated MQTT configuration
- Fixed entity ID conflicts with static year sensors

### 📚 Documentation
- Updated README with new features and configuration examples
- Added technical documentation (DOCS.md) with detailed explanations
- All documentation now available in English

### ⚠️ Breaking Changes
**None** - This release is fully backward compatible. Existing sensors will continue to work.

### 📦 Migration Guide
1. Update add-on files
2. Add `billing_start_month` to your configuration
3. Restart add-on
4. New sensors will appear automatically

---

## [1.0.0] - 2026-02-05

### 🎉 Initial Release
- Automatic Playwright login with Azure B2C SAML
- MQTT Auto-Discovery integration
- Heating, hot water, cold water sensors per room
- 12 months consumption history
- DIN comparison support
