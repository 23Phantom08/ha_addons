# Minol Customer Portal - Technical Documentation

## Architecture

```
main.py → minol_connector.py → Minol Portal
   ↓
MQTT Broker → Home Assistant
```

**Components:**
- `main.py`: MQTT client, orchestration, HA discovery
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

POST /minol.com~kundenportal~em~web/resources/svcweb/getUserTenants
     → Returns tenant/property info

POST /minol.com~kundenportal~em~web/resources/svcweb/getVerbPdf
     → Returns consumption data (12 months)
```

## Data Structure

```python
{
  "heating": {
    "total_consumption": 1234.5,          # Total kWh
    "timeline": [
      {"label": "Jan", "value": 123.4},   # Monthly values
      {"label": "REF", "value": 130.0}    # DIN reference
    ],
    "by_room": [{
      "room_name": "Living Room",
      "device_number": "12345678",         # Unique meter ID
      "consumption": 456.7,
      "reading": 1234,                     # Current reading
      "initial_reading": 777               # Start value
    }]
  },
  "hot_water": {...},
  "cold_water": {...}
}
```

## MQTT Message Format

**Discovery Config:**
```json
{
  "name": "Minol Heating Total",
  "unique_id": "minol_heating_total",
  "state_topic": "minol/heating_total/state",
  "unit_of_measurement": "kWh",
  "device_class": "energy",
  "state_class": "total_increasing",
  "json_attributes_topic": "minol/heating_total/attributes"
}
```

**State:** `123.4` (numeric value only)

**Attributes:** 
```json
{
  "monthly_data": [...],
  "din_comparison_percent": 15.2,
  "last_update": "2026-02-04T18:00:00Z"
}
```

## Entity ID Patterns

- **Total sensors:** `sensor.minol_{category}_total`
  - Example: `sensor.minol_heating_total`
- **Room sensors:** `sensor.minol_{category}_{room}_{device_number}`
  - Example: `sensor.minol_heating_livingroom_12345678`
- **Customer info:** `sensor.minol_customer_info`

## DIN Comparison Calculation

Compares actual consumption vs. DIN reference standard:

```python
actual = sum(v for v in timeline if label != "REF")
reference = sum(v for v in timeline if label == "REF")
din_percent = ((actual - reference) / reference) * 100

# Positive = above reference, Negative = below reference
```

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
- Error stack traces

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Login timeout | Increase timeout: `page.goto(url, timeout=120000)` |
| No SAML response | Azure B2C UI changed → Update selector in code |
| No sensors in HA | Reload MQTT integration or restart HA |
| Out of memory | Allocate minimum 512 MB RAM to add-on |
| Connection refused | Check MQTT broker status & credentials |

## Python Dependencies

```python
playwright==1.40.0      # Browser automation
paho-mqtt==1.6.1        # MQTT client
requests==2.31.0        # HTTP requests
beautifulsoup4==4.12.2  # HTML parsing
```

**System dependencies:**
Chromium + libraries (see Dockerfile)

---

**License:** MIT
