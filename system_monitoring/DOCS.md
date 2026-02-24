# 🖥️ System Monitoring - Technical Docs

## Architecture

```
Home Assistant
    ↓
Add-on Container
    ├─ server.js (Node.js)
    └─ script.js (Monitoring Logic)
    ↓
MQTT Broker
    ↓
Home Assistant Entities
```

## How It Works

1. Add-on starts every 5 seconds (configurable)
2. Collects system stats: CPU, Memory, Disk, Network, Temperature
3. Publishes to MQTT topics
4. Home Assistant discovers entities automatically

## MQTT Payload Format

```json
{
  "cpu": 45.2,
  "memory": 62.5,
  "disk": 78.1,
  "network_rx": 1024000,
  "network_tx": 512000,
  "temperature": 52.3
}
```

## File Structure

| File | Purpose |
|------|---------|
| config.yaml | Add-on configuration |
| server.js | Main Node.js server |
| script.js | Monitoring logic |
| package.json | Dependencies (mqtt) |
| Dockerfile | Container definition |
| run | Startup script |

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| mqtt_broker | string | homeassistant | MQTT broker hostname |
| mqtt_port | int | 1883 | MQTT port |
| mqtt_user | string | empty | MQTT username |
| mqtt_password | string | empty | MQTT password |
| mqtt_topic_prefix | string | homeassistant/sensor/system_monitor | Topic prefix |
| update_interval | int | 5 | Update interval (seconds) |
| enable_mqtt | bool | true | Enable MQTT publishing |

## Dependencies

- **Node.js** (in Dockerfile)
- **mqtt** (npm package v5.0.0)

## Metrics Collected

| Metric | Unit | Description |
|--------|------|-------------|
| CPU | % | CPU usage percentage |
| Memory | % | RAM usage percentage |
| Disk | % | Root filesystem usage |
| Network RX | bytes | Network received |
| Network TX | bytes | Network transmitted |
| Temperature | °C | System temperature |

## Home Assistant Integration

Add to `configuration.yaml`:

```yaml
mqtt:
  broker: homeassistant
  
sensor:
  - platform: mqtt
    name: "CPU Usage"
    state_topic: "homeassistant/sensor/system_monitor/cpu"
    unit_of_measurement: "%"
```

## Troubleshooting

**Add-on won't start:**
- Check Docker daemon running
- Verify MQTT broker accessible
- Check logs: Settings → Add-ons → System Monitoring → Logs

**No MQTT data:**
- Verify MQTT credentials in config
- Check mosquitto is running
- Ensure network connectivity

**High CPU usage:**
- Increase `update_interval` (e.g., 10 or 30 seconds)
- Check for zombie processes

## Docker Build

```bash
docker build -t ha-system-monitor .
docker run -it ha-system-monitor
```

## Local Testing

```bash
npm install
node server.js
```

---

**Version**: 1.0.0 | Last Updated: 2026-02-23
