import time
import json
import os
import logging
import sys
import paho.mqtt.client as mqtt
from datetime import datetime
from minol_connector import MinolConnector

OPTIONS_PATH = '/data/options.json'

def load_config():
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH, 'r') as f:
            conf = json.load(f)
            # Setze Defaults falls nicht in Config
            if "ww_factor" not in conf: conf["ww_factor"] = 58.15
            if "billing_start_month" not in conf: conf["billing_start_month"] = 9
            return conf
    return {
        "minol_email": os.environ.get("MINOL_EMAIL"),
        "minol_password": os.environ.get("MINOL_PASSWORD"),
        "mqtt_host": os.environ.get("MQTT_HOST", "localhost"),
        "mqtt_port": int(os.environ.get("MQTT_PORT", 1883)),
        "mqtt_user": os.environ.get("MQTT_USER"),
        "mqtt_password": os.environ.get("MQTT_PASSWORD"),
        "scan_interval_hours": 6,
        "ww_factor": 58.15,
        "billing_start_month": 9,
        "base_url": "https://webservices.minol.com",
        "log_level": "INFO"
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
        logger.error(f"MQTT Fehler: {e}"); sys.exit(1)

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
    if state_class: payload["state_class"] = state_class
    if attributes_topic: payload["json_attributes_topic"] = attributes_topic
    mqtt_client.publish(topic, json.dumps(payload), qos=0, retain=True)

def publish_state(unique_id, value):
    mqtt_client.publish(f"minol/{unique_id}/state", str(value), qos=0, retain=True)

def publish_attributes(unique_id, attributes):
    mqtt_client.publish(f"minol/{unique_id}/attributes", json.dumps(attributes), qos=0, retain=True)

def run_sync():
    connector = MinolConnector(config["minol_email"], config["minol_password"], config["base_url"])
    logger.info("Starte Synchronisierung...")
    connector.login()
    if not getattr(connector, "_authenticated", False): return

    connector.get_user_tenants()
    data = connector.get_consumption_data(months_back=24, force_update=True)
    if not data: return

    user_info = getattr(connector, "user_info", {})
    
    # --- 0. Customer Info Sensor ---
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

        publish_discovery_config(
            "info", uid, "Minol Customer Info", "", "mdi:account", None, 
            state_class=None, attributes_topic=f"minol/{uid}/attributes"
        )
        publish_state(uid, customer_attrs["customer_number"])
        publish_attributes(uid, customer_attrs)
    
    now = datetime.now()
    
    # Abrechnungsperiode aus Config (Benutzer trägt seinen Monat ein)
    b_start_month = config.get("billing_start_month", 9)
    logger.info(f"📅 Abrechnungsperiode aus Config: Monat {b_start_month}")
    
    ww_faktor = config.get("ww_factor", 58.15)
    
    current_month, current_year = now.month, now.year
    if current_month >= b_start_month:
        b_curr_start, b_curr_end = current_year, current_year + 1
        b_last_start, b_last_end = current_year - 1, current_year
        months_active = current_month - b_start_month + 1
    else:
        b_curr_start, b_curr_end = current_year - 1, current_year
        b_last_start, b_last_end = current_year - 2, current_year - 1
        months_active = (12 - b_start_month) + current_month + 1

    cats = {
        "heating": ("Heizung", "kWh", "mdi:radiator", "energy"),
        "hot_water": ("Warmwasser", "m³", "mdi:water-thermometer", "water"),
        "cold_water": ("Kaltwasser", "m³", "mdi:water-pump", "water")
    }

    # --- 1. Perioden-Sensoren ---
    for k, (name, unit, icon, devc) in cats.items():
        if k in data and "timeline" in data[k]:
            real_months = [e for e in data[k]["timeline"] if e.get("label") != "REF"]
            
            # Aktuelle Periode
            raw_curr = sum(float(e.get("value", 0) or 0) for e in real_months[-months_active:])
            val_curr = round(raw_curr / ww_faktor, 2) if k == "hot_water" else round(raw_curr, 2)
            uid_c = f"{k}_period_current"
            publish_discovery_config(k, uid_c, f"Minol {name} Aktuelle Periode", unit, icon, devc, "total_increasing", f"minol/{uid_c}/attributes")
            publish_state(uid_c, val_curr)
            publish_attributes(uid_c, {"zeitraum": f"{b_curr_start}/{b_curr_end}", "monate_aktiv": months_active})

            # Letzte Periode
            s_idx, e_idx = len(real_months) - months_active - 12, len(real_months) - months_active
            raw_last = sum(float(e.get("value", 0) or 0) for e in real_months[s_idx:e_idx]) if s_idx >= 0 else 0
            val_last = round(raw_last / ww_faktor, 2) if k == "hot_water" else round(raw_last, 2)
            uid_l = f"{k}_period_last"
            publish_discovery_config(k, uid_l, f"Minol {name} Letzte Periode", unit, icon, devc, "total", f"minol/{uid_l}/attributes")
            publish_state(uid_l, val_last)
            publish_attributes(uid_l, {"zeitraum": f"{b_last_start}/{b_last_end}", "monate_voll": 12 if s_idx >= 0 else 0})

    # --- 2. Zimmer-Sensoren (Ohne WW-Faktor, Null-Werte gefiltert) ---
    def process_rooms(category_key, category_name, unit, icon, device_class):
        if category_key not in data or "by_room" not in data[category_key]: return
        for room in data[category_key]["by_room"]:
            r_name = room.get("room_name", "Unknown")
            device_num = str(room.get("device_number", "unknown"))
            
            safe_room = ''.join(e for e in r_name if e.isalnum()).lower()
            uid = f"{category_key}_{safe_room}_{device_num}"
            
            # KEIN Warmwasser-Faktor bei Räumen! Nur RAW-Werte
            val = room.get("consumption", 0)
            
            # Filtere Null-Werte raus
            if val <= 0:
                continue
            
            publish_discovery_config(category_key, uid, f"Minol {r_name} {category_name} ({device_num})", unit, icon, device_class, "total_increasing", f"minol/{uid}/attributes")
            publish_state(uid, val)
            
            attrs = {
                "room_name": r_name,
                "device_number": device_num,
                "current_reading": room.get("reading", 0),
                "initial_reading": room.get("initial_reading", 0),
                "monthly_history": data[category_key].get("timeline", [])
            }
            publish_attributes(uid, attrs)

    process_rooms("heating", "Heizung", "kWh", "mdi:radiator", "energy")
    process_rooms("hot_water", "Warmwasser", "m³", "mdi:water-thermometer", "water")
    process_rooms("cold_water", "Kaltwasser", "m³", "mdi:water-pump", "water")
    
    logger.info("Sync erfolgreich beendet.")

if __name__ == "__main__":
    connect_mqtt()
    while True:
        try: run_sync()
        except Exception as e: logger.error(f"Fehler: {e}")
        time.sleep(config.get("scan_interval_hours", 6) * 3600)
    
