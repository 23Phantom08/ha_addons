# Minol Customer Portal

Automatically fetches your Minol consumption data and makes it available in Home Assistant.

## Features

- ✅ Automatic login (Playwright)
- ✅ Heating, hot water, cold water per room
- ✅ 12 months history (Attributes)
- ✅ MQTT Auto-Discovery

## Configuration

```yaml
minol_email: "your-email@example.com"
minol_password: "your-password"
mqtt_host: "core-mosquitto"
mqtt_port: 1883
scan_interval_hours: 12  # How often to fetch (6-24h)
```

## Sensors

### Total
- Heating Total (kWh)
- Hot Water Total (m³)
- Cold Water Total (m³)

### Per Room
- Each room with meter number
- e.g. "Living Room Heating (12345678)"

### Attributes
- Monthly values
- DIN comparison %
- Meter reading

## Troubleshooting

**No sensors?**
- Check MQTT Integration
- Set log level to `DEBUG`

**Login fails?**
- Check email/password
- Automatic retry after 1-2 min

**Playwright Error?**
- At least 512 MB RAM required

## MQTT Topics

```
minol/heating_total/state
minol/hot_water_total/state
minol/heating_livingroom_12345678/state
```

Auto-Discovery runs via `homeassistant/sensor/minol/#`

## Support

For issues → Create GitHub Issue with debug logs

---

**Version:** 1.0.0 | **License:** MIT
