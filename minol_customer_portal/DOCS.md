# Minol Customer Portal - Technical Documentation

## Architecture

```
main.py → minol_connector.py → Minol Portal
   ↓
MQTT Broker → Home Assistant
```

**Components:**
- `main.py`: MQTT client, orchestration, HA discovery, billing period logic
- `minol_connector.py`: Playwright auth, API requests, data parsing

## Authentication Flow

Azure B2C SAML via Playwright:
1. Initial request redirects to `minolauth.b2clogin.com`
2. Automated login with email/password
3. Extract base64 SAML response from page
4. POST SAML to `/saml2/sp/acs` endpoint
5. Receive `JSESSIONID` session cookie
6. Use cookie for subsequent API calls

## API Endpoints

```
Base URL: https://webservices.minol.com

GET  /minol.com~kundenportal~em~web/resources/monitoring/index.html
     → Triggers SAML redirect

POST /saml2/sp/acs
     → Accepts SAML response, creates session

POST /minol.com~kundenportal~em~web/rest/EMData/getUserTenants
     → Returns tenant/property info

POST /minol.com~kundenportal~em~web/rest/EMData/readData
     → Returns consumption data (up to 24 months)
```

## Data Structure

```python
{
  "heating": {
    "by_room": [{
      "room_name": "Storage Room",
      "device_number": "6ZRI8911235238",   # Unique meter ID
      "consumption": 677.0,                # kWh
      "reading": 1234,                     # Current reading
      "initial_reading": 777               # Start value
    }],
    "timeline": [
      {"period": "202601", "value": 123.4, "label": "Jan 26"},
      {"label": "REF", "value": 130.0}     # DIN reference
    ],
    "total_consumption": 1234.5            # Total kWh
  },
  "hot_water": {...},
  "cold_water": {...}
}
```

## Billing Period Calculation

**Configuration:**
```yaml
billing_start_month: 9  # September
```

**Logic:**
- Current period: Sep 2025 - Feb 2026 (6 months counted)
- Last period: Sep 2024 - Aug 2025 (12 full months)

**Calculation:**
```python
if current_month >= billing_start_month:
    period_start = current_year
    months_counted = current_month - billing_start_month + 1
else:
    period_start = current_year - 1
    months_counted = (12 - billing_start_month) + current_month + 1

# Sum last N months from timeline
current_period = sum(timeline[-months_counted:])
last_period = sum(timeline[-months_counted-12:-months_counted])
```

## Hot Water Correction Factor

**Issue:** Minol API returns raw hot water values (e.g. 913.01 m³)  
**Solution:** Divide by correction factor 58.15

**Applied to:**
- ✅ Billing period sensors (`period_current`, `period_last`)
- ❌ Room sensors (show raw API values)

```python
ww_factor = 58.15
corrected_value = raw_value / ww_factor
# 913.01 / 58.15 = 15.70 m³
```

## MQTT Message Format

**Discovery Config:**
```json
{
  "name": "Minol Heating Current Period",
  "unique_id": "minol_heating_period_current",
  "state_topic": "minol/heating_period_current/state",
  "unit_of_measurement": "kWh",
  "device_class": "energy",
  "state_class": "total_increasing",
  "json_attributes_topic": "minol/heating_period_current/attributes"
}
```

**State:** `421.00` (numeric value only)

**Attributes:**
```json
{
  "zeitraum": "2025/2026",
  "monate_aktiv": 6,
  "last_update": "2026-02-10T10:32:00Z"
}
```

## Entity ID Patterns

- **Billing periods:** `sensor.minol_{category}_period_{current|last}`
  - Example: `sensor.minol_heating_period_current`
  - Example: `sensor.minol_hot_water_period_last`
- **Room sensors:** `sensor.minol_{category}_{room}_{device_number}`
  - Example: `sensor.minol_heating_storageroom_6zri8911235238`
- **Customer info:** `sensor.minol_customer_info`

## Zero-Value Filtering

Room sensors with consumption ≤ 0 are not created:

```python
if val <= 0:
    continue  # Skip sensor creation
```

This prevents cluttering HA with inactive meters.

## Performance Metrics

| Metric | Value |
|--------|-------|
| Idle RAM | ~100 MB |
| Login RAM | ~400 MB |
| Login time | 10-30s |
| Data fetch | 5-10s |
| **Recommended** | 512 MB RAM |
| **Update interval** | 12h |

## Debug Mode

Enable detailed logging:
```yaml
log_level: "DEBUG"
```

**Debug output includes:**
- Playwright page navigation steps
- SAML response extraction
- API request/response bodies
- MQTT topic publishing
- Billing period calculations
- Error stack traces

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Login timeout | Increase timeout: `page.goto(url, timeout=120000)` |
| No SAML response | Azure B2C UI changed → Update selector in code |
| No sensors in HA | Reload MQTT integration or restart HA |
| Out of memory | Allocate minimum 512 MB RAM to add-on |
| Wrong billing period | Set correct `billing_start_month` in config |
| Hot water values too high | Check `ww_factor` setting (default: 58.15) |

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `minol_email` | string | - | Portal login email |
| `minol_password` | string | - | Portal password |
| `mqtt_host` | string | core-mosquitto | MQTT broker hostname |
| `mqtt_port` | int | 1883 | MQTT broker port |
| `scan_interval_hours` | int | 12 | Hours between updates |
| `billing_start_month` | int | 9 | Billing period start month (1-12) |
| `ww_factor` | float | 58.15 | Hot water correction factor |
| `log_level` | string | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |

## Python Dependencies

```python
playwright==1.40.0      # Browser automation
paho-mqtt==1.6.1        # MQTT client
requests==2.31.0        # HTTP requests
```

**System dependencies:**
Chromium + libraries (see Dockerfile)

---

**License:** MIT
