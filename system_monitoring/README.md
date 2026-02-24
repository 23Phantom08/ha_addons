# 🖥️ Home Assistant System Monitoring

System monitoring add-on for Home Assistant that publishes CPU, memory, disk, and network stats via MQTT.

## Features

- 📊 Real-time system stats (CPU, Memory, Disk, Network)
- 📡 MQTT publishing (no UI needed)
- 🔄 Configurable update interval (default: 5s)
- 🏠 Home Assistant discovery
- 🐧 Linux/Docker compatible

## Configuration

```yaml
mqtt_broker: "homeassistant"
mqtt_port: 1883
mqtt_user: ""
mqtt_password: ""
mqtt_topic_prefix: "homeassistant/sensor/system_monitor"
update_interval: 5
enable_mqtt: true
```

## MQTT Topics

```
homeassistant/sensor/system_monitor/cpu
homeassistant/sensor/system_monitor/memory
homeassistant/sensor/system_monitor/disk
homeassistant/sensor/system_monitor/network
homeassistant/sensor/system_monitor/temperature
```

## Requirements

- Home Assistant 2024.1+
- MQTT Broker (mosquitto)
- Linux/Docker environment

## Troubleshooting

- **MQTT not publishing?** Check broker is running
- **Stats missing?** Verify MQTT credentials
- **Disk usage 0%?** Check Docker volume permissions

---

**Version**: 1.0.0 | Made with ❤️ for Home Assistant
