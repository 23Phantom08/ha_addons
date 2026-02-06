import time
import json
import os
import logging
import sys
import paho.mqtt.client as mqtt
from minol_connector import MinolConnector

OPTIONS_PATH = '/data/options.json'

def load_config():
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH, 'r') as f:
            return json.load(f)
    return {
        "minol_email": os.environ.get("MINOL_EMAIL"),
        "minol_password": os.environ.get("MINOL_PASSWORD"),
        "mqtt_host": os.environ.get("MQTT_HOST", "localhost"),
        "mqtt_port": int(os.environ.get("MQTT_PORT", 1883)),
        "mqtt_user": os.environ.get("MQTT_USER"),
        "mqtt_password": os.environ.get("MQTT_PASSWORD"),
        "scan_interval_hours": 6,
        "base_url": os.environ.get("BASE_URL", "https://webservices.minol.com"),
        "log_level": os.environ.get("LOG_LEVEL", "INFO")
    }

config = load_config()
logging.basicConfig(level=getattr(logging, config.get("log_level", "INFO").upper()), format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MinolBridge")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
if config.get("mqtt_user") and config.get("mqtt_password"):
    mqtt_client.username_pw_set(config["mqtt_user"], config["mqtt_password"])

def connect_mqtt():
    try:
        mqtt_client.connect(config["mqtt_host"], config["mqtt_port"], 60)
        mqtt_client.loop_start()
        logger.info("Verbunden mit MQTT")
    except Exception as e:
        logger.error(f"MQTT Fehler: {e}")
        sys.exit(1)

def publish_discovery_config(sensor_type, unique_id, name, unit, icon, device_class, state_class=None, attributes_topic=None):
    topic = f"homeassistant/sensor/minol/{unique_id}/config"
    payload = {
        "name": name,
        "unique_id": f"minol_{unique_id}",
        "state_topic": f"minol/{unique_id}/state",
        "unit_of_measurement": unit,
        "device_class": device_class,
        "icon": icon,
        "platform": "mqtt",
        "device": {"identifiers": ["minol_account"], "name": "Minol Customer Portal", "manufacturer": "Minol"}
    }
    if state_class:
        payload["state_class"] = state_class
    if attributes_topic:
        payload["json_attributes_topic"] = attributes_topic
    mqtt_client.publish(topic, json.dumps(payload), qos=0, retain=True)

def publish_state(unique_id, value):
    mqtt_client.publish(f"minol/{unique_id}/state", str(value), qos=0, retain=True)

def publish_attributes(unique_id, attributes):
    mqtt_client.publish(f"minol/{unique_id}/attributes", json.dumps(attributes), qos=0, retain=True)
    
def run_sync():
    """
    Main sync cycle: authenticate, fetch data, and publish to MQTT.
    """
    connector = MinolConnector(config["minol_email"], config["minol_password"], config["base_url"])

    logger.info("Starting authentication...")
    connector.login()
    if not getattr(connector, "_authenticated", False):
        logger.error("Authentication failed. Retrying next cycle.")
        return

    # Nutzerdaten & Verbräuche abrufen
    connector.get_user_tenants()
    data = connector.get_consumption_data(months_back=12, force_update=True)
    if not data:
        logger.error("No data received.")
        return

    # --- 1. Nutzer-Info Sensor (Exakt wie beim anderen User) ---
    user_info = getattr(connector, "user_info", {})
    if user_info:
        logger.info("Publishing customer data sensor...")
        addr = f"{user_info.get('addrStreet','')} {user_info.get('addrHouseNum','')} {user_info.get('addrPostalCode','')} {user_info.get('addrCity','')}".strip()
        
        uid = "customer_info"
        customer_attrs = {
            "email": user_info.get("email", ""),
            "customer_number": user_info.get("userNumber", ""),
            "tenant_number": str(user_info.get("nenr", "000003")).strip(),
            "property_number": str(user_info.get("lgnr", "")).strip(),
            "floor": user_info.get("geschossText", ""),
            "position": user_info.get("lageText", ""),
            "address": addr,
            "name": user_info.get("name", ""),
            "move_in_date": user_info.get("einzugMieter", ""),
        }

        # WICHTIG: state_class=None für diesen Text/ID-Sensor
        publish_discovery_config(
            "info",
            uid,
            "Minol Customer Info",
            "",
            "mdi:account",
            None,
            state_class=None,
            attributes_topic=f"minol/{uid}/attributes"
        )
        publish_state(uid, customer_attrs["customer_number"])
        publish_attributes(uid, customer_attrs)

    # Hilfsfunktion für DIN-Vergleich
    def calculate_din_comparison(timeline):
        if not timeline: return None
        try:
            act = sum(float(e.get("value", 0) or 0) for e in timeline if e.get("label") != "REF")
            ref = sum(float(e.get("value", 0) or 0) for e in timeline if e.get("label") == "REF")
            return round(((act - ref) / ref) * 100, 1) if ref > 0 else None
        except: return None

    # --- 2. Gesamtverbräuche (Totals) ---
    cats = {
        "heating": ("Heating Total", "kWh", "mdi:radiator", "energy"),
        "hot_water": ("Hot Water Total", "m³", "mdi:water-thermometer", "water"),
        "cold_water": ("Cold Water Total", "m³", "mdi:water-pump", "water")
    }

    for k, (name, unit, icon, devc) in cats.items():
        if k in data and "total_consumption" in data[k]:
            timeline = data[k].get("timeline", [])
            attrs = {
                "monthly_data": timeline,
                "din_comparison_percent": calculate_din_comparison(timeline),
                "last_update": data.get("timestamp", "")
            }
            publish_discovery_config(k, f"{k}_total", f"Minol {name}", unit, icon, devc, state_class="total_increasing", attributes_topic=f"minol/{k}_total/attributes")
            publish_state(f"{k}_total", data[k]["total_consumption"])
            publish_attributes(f"{k}_total", attrs)

    # --- 3. Raum-Sensoren (Mit Zählernummern im Namen & ID) ---
    def process_rooms(category_key, category_name, unit, icon, device_class):
        if category_key not in data or "by_room" not in data[category_key]: return
        for room in data[category_key]["by_room"]:
            r_name = room.get("room_name", "Unknown")
            device_num = room.get("device_number", "")
            
            # Eindeutige ID mit Zählernummer für HA
            safe_room = "".join(e for e in r_name if e.isalnum()).lower()
            uid = f"{category_key}_{safe_room}_{device_num}"
            
            val = room.get("consumption", 0)
            # Zählernummer im Anzeigenamen (Friendly Name)
            sensor_name = f"Minol {r_name} {category_name} ({device_num})"

            attrs = {
                "room_name": r_name,
                "device_number": device_num,
                "current_reading": room.get("reading", 0),
                "initial_reading": room.get("initial_reading", 0),
                "monthly_history": data[category_key].get("timeline", [])
            }
            publish_discovery_config(category_key, uid, sensor_name, unit, icon, device_class, state_class="total_increasing", attributes_topic=f"minol/{uid}/attributes")
            publish_state(uid, val)
            publish_attributes(uid, attrs)

    process_rooms("heating", "Heating", "kWh", "mdi:radiator", "energy")
    process_rooms("hot_water", "Hot Water", "m³", "mdi:water-thermometer", "water")
    process_rooms("cold_water", "Cold Water", "m³", "mdi:water-pump", "water")

    logger.info("Sync completed. All sensors with device numbers published.")

if __name__ == "__main__":
    connect_mqtt()
    while True:
        try:
            run_sync()
        except Exception as e:
            logger.error(f"Fehler: {e}")
        time.sleep(config.get("scan_interval_hours", 12) * 3600)





