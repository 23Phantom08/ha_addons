# Minol Customer Portal

Automatically fetches your Minol consumption data and makes it available in Home Assistant.

## Features

- ✅ Automatic login (Playwright)
- ✅ Heating, hot water, cold water per room
- ✅ **Current & Last billing period sensors**
- ✅ **Automatic hot water correction factor (58.15)**
- ✅ **Zero-value filtering** (only active sensors shown)
- ✅ MQTT Auto-Discovery
- ✅ Customer information sensor

## Configuration

```yaml
minol_email: "your-email@example.com"
minol_password: "your-password"
mqtt_host: "core-mosquitto"
mqtt_port: 1883
scan_interval_hours: 12       # How often to fetch (6-24h)
billing_start_month: 9        # Your billing period start (1-12)
```

### Billing Period Configuration

Set your billing period start month (1-12):
- **September:** `billing_start_month: 9` (common default)
- **March:** `billing_start_month: 3`
- **January:** `billing_start_month: 1`

## Sensors

### Billing Period Sensors (NEW!)
- **Heating Current Period** (kWh) - Current billing period consumption
- **Heating Last Period** (kWh) - Previous full billing period
- **Hot Water Current Period** (m³) - With automatic correction factor
- **Hot Water Last Period** (m³) - With automatic correction factor
- **Cold Water Current Period** (m³)
- **Cold Water Last Period** (m³)

### Per Room
- Each room with meter number
- e.g. "Storage Room Heating (6ZRI8911235238)"
- **Only rooms with consumption > 0 shown**

### Customer Info
- Customer number, address, move-in date
- Tenant & property number
- All details as attributes

### Attributes
- Monthly values (12 months)
- DIN comparison %
- Billing period details
- Meter readings

## Hot Water Correction

The Minol API returns raw hot water values that need correction:
- **Factor:** 58.15 (configurable via `ww_factor`)
- **Applied to:** Billing period sensors only
- **Room sensors:** Show raw values from API

## Troubleshooting

**No sensors?**
- Check MQTT Integration
- Set log level to `DEBUG`
- Restart Home Assistant

**Login fails?**
- Check email/password
- Automatic retry after 1-2 min
- Check add-on logs

**Playwright Error?**
- At least 512 MB RAM required
- Increase memory in add-on settings

**Wrong billing period?**
- Set `billing_start_month` in config
- Example: September = 9, March = 3

## MQTT Topics

```
minol/heating_period_current/state
minol/heating_period_last/state
minol/hot_water_period_current/state
minol/heating_storageroom_6zri8911235238/state
minol/customer_info/state
```

Auto-Discovery runs via `homeassistant/sensor/minol/#`

## Support

For issues → Create GitHub Issue with debug logs

---

**License:** MIT
