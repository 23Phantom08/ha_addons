#!/usr/bin/env python3
"""
Digimeto Customer Portal for Home Assistant
Vollautomatisch inkl. SAML-Login via Playwright, dynamischer ID-Erkennung 
und 7-Tage & 13-Monate Historie.
"""

import os
import sys
import time
import json
import logging
import requests
import urllib.parse
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
from playwright.sync_api import sync_playwright

# --- KONFIGURATION ---
DIGIMETO_USERNAME = os.getenv('DIGIMETO_USERNAME', '')
DIGIMETO_PASSWORD = os.getenv('DIGIMETO_PASSWORD', '')
MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_TOPIC_PREFIX = os.getenv('MQTT_TOPIC_PREFIX', 'digimeto')
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', 3600))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DIGIMETO_BASE_URL = "https://vdis5.digimeto.de"
DIGIMETO_LOGIN_URL = f"{DIGIMETO_BASE_URL}/login"

class DigimetoAPI:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.state_file = "/data/digimeto_auth_state.json"
        self.mp_id1 = None
        self.mp_id2 = None
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept-Language': 'de-DE,de;q=0.9'
        })
        self._load_saved_state()

    def _load_saved_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    for cookie in state.get('cookies', []):
                        self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
                self._update_xsrf_from_cookie()
                logger.info("Gespeicherte Session geladen.")
            except Exception as e:
                logger.warning(f"Auth-State Fehler beim Laden: {e}")

    def _update_xsrf_from_cookie(self):
        token = self.session.cookies.get('XSRF-TOKEN')
        if token:
            self.session.headers.update({'X-XSRF-TOKEN': urllib.parse.unquote(token)})
            return True
        return False

    def _fetch_dynamic_ids(self):
        logger.info("Ermittle Zählpunkt-IDs...")
        try:
            url = f"{DIGIMETO_BASE_URL}/sidebarMultiMp/rlm"
            token = self.session.cookies.get('XSRF-TOKEN')
            if token: url += f"?ct={urllib.parse.quote(token)}"
            
            resp = self.session.get(url, timeout=20)
            if resp.status_code == 200:
                # Sicherstellen, dass die Antwort JSON ist
                try:
                    data = resp.json()
                except:
                    return False
                
                if not isinstance(data, list): return False

                for root_item in data:
                    if not isinstance(root_item, dict): continue
                    for list_item in root_item.get('childs', []):
                        for mp in list_item.get('childs', []):
                            if mp.get('type') == 'mp':
                                m_id = mp.get('id')
                                for line in mp.get('childs', []):
                                    if line.get('type') == 'line':
                                        self.mp_id1 = m_id
                                        self.mp_id2 = line.get('id')
                                        logger.info(f"Zählpunkt-IDs ermittelt: {self.mp_id1}/{self.mp_id2}")
                                        return True
            return False
        except Exception as e:
            logger.error(f"Fehler bei ID-Ermittlung: {e}")
            return False

    def login(self):
        logger.info("Versuche Login bei Digimeto...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
                context = browser.new_context()
                page = context.new_page()
                page.goto(DIGIMETO_LOGIN_URL, wait_until="networkidle")
                page.fill('input[name="_username"]', self.username)
                page.fill('input[name="_password"]', self.password)
                page.check('input[name="_remember_me"]')
                page.click('button[type="submit"]')
                page.wait_for_function("() => !window.location.href.includes('/login')", timeout=60000)
                page.goto(f"{DIGIMETO_BASE_URL}/analytics/getanalysepage", wait_until="networkidle")
                time.sleep(2)
                state = context.storage_state()
                with open(self.state_file, 'w') as f:
                    json.dump(state, f)
                for cookie in state.get('cookies', []):
                    self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
                self._update_xsrf_from_cookie()
                browser.close()
                logger.info("Login erfolgreich!")
                return True
        except Exception as e:
            logger.error(f"Login fehlgeschlagen: {e}")
            return False

    def get_meter_data(self):
        try:
            if not self.mp_id1 or not self.mp_id2:
                if not self._fetch_dynamic_ids():
                    if self.login(): self._fetch_dynamic_ids()
                    else: return None

            logger.info("Rufe Zählerdaten ab...")
            now = datetime.now()
            start_date = now - timedelta(days=1095)  # 3 Jahre Historie
            start_str = start_date.strftime("%Y-%m-%dT00:00:00+01:00")
            end_str = now.strftime("%Y-%m-%dT%H:%M:%S+01:00")
            
            periods = ["15mins", "days", "months", "years"]
            all_raw_data = []
            
            for p in periods:
                url = f"{DIGIMETO_BASE_URL}/data/mpline/genericto/{self.mp_id1}/{self.mp_id2}/{urllib.parse.quote(start_str)}/{urllib.parse.quote(end_str)}/{p}"
                token = self.session.cookies.get('XSRF-TOKEN')
                if token: url += f"?ct={urllib.parse.quote(token)}"
                
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 401 or "/login" in resp.url:
                    if self.login(): return self.get_meter_data()
                    return None
                
                if resp.status_code == 200:
                    try:
                        json_data = resp.json()
                        json_data['aggregationperiod'] = p
                        all_raw_data.append(json_data)
                    except: continue
            
            logger.info("Zählerdaten erfolgreich abgerufen")
            return self.parse_data(all_raw_data)
        except Exception as e:
            logger.error(f"Fehler beim Datenabruf: {e}")
            return None

    def parse_data(self, raw_data_list):
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            current_year = now.year
            
            parsed = {
                'timestamp': now.isoformat(),
                'consumption': {
                    'current': 0, 
                    'today': 0, 
                    'days_last': 0, 
                    'years_last': 0,
                    'current_year': 0  # Verbrauch im aktuellen Jahr
                },
                'history': {
                    'days': {}, 
                    'months': {},
                    'years': {}  # Letzte 3 Jahre
                },
                'meter': {'reading': 0}
            }

            for data in raw_data_list:
                p = data.get('aggregationperiod')
                vals = data.get('values', [])
                tss = data.get('timestamps', [])

                if 'maloId' not in parsed['meter'] and data.get('details'):
                    d = data.get('details', {})
                    parsed['meter'].update({
                        'maloId': d.get('maloId', ''),
                        'metpoint': data.get('metpointname', ''),
                        'unit': data.get('unit', 'kWh'),
                        'mq': d.get('mq', '')
                    })

                if p == '15mins' and vals:
                    # Aktuelle Leistung in Watt
                    parsed['consumption']['current'] = round(vals[-1] * 4000, 0)
                    
                    # Heute summieren
                    t_sum = 0
                    for ts, val in zip(tss[-150:], vals[-150:]):
                        if ts.split('T')[0] == today_str: 
                            t_sum += val
                    parsed['consumption']['today'] = round(t_sum, 3)

                elif p == 'days' and vals:
                    # Letzte 7 Tage
                    for i, val in enumerate(reversed(vals[-7:])):
                        parsed['history']['days'][f'day_{i+1}'] = round(val, 3)
                    parsed['consumption']['days_last'] = round(vals[-1], 3)
                    
                    # Verbrauch im aktuellen Jahr (summiere alle Tage von diesem Jahr)
                    year_sum = 0
                    for ts, val in zip(tss, vals):
                        try:
                            if ts.split('-')[0] == str(current_year):
                                year_sum += val
                        except:
                            continue
                    parsed['consumption']['current_year'] = round(year_sum, 3)

                elif p == 'months' and vals:
                    # Letzte 13 Monate
                    for i, val in enumerate(reversed(vals[-13:])):
                        parsed['history']['months'][f'month_{i+1}'] = round(val, 3)

                elif p == 'years' and vals and tss:
                    # Gesamtzählerstand (letzter Jahreswert)
                    parsed['meter']['reading'] = round(vals[-1], 3)
                    parsed['consumption']['years_last'] = round(vals[-1], 3)
                    
                    # Letzte 3 Jahre - FESTE Keys: year_1, year_2, year_3
                    # year_1 = aktuelles/letztes Jahr, year_2 = vorletztes Jahr, year_3 = vor 3 Jahren
                    for i, (ts, val) in enumerate(zip(reversed(tss[-3:]), reversed(vals[-3:]))):
                        try:
                            year = ts.split('-')[0]  # Jahr für Display-Name
                            parsed['history']['years'][f'year_{i+1}'] = {
                                'value': round(val, 3),
                                'year': year  # Jahr als Metadaten für Display
                            }
                        except:
                            # Fallback ohne Jahr-Parsing
                            parsed['history']['years'][f'year_{i+1}'] = {
                                'value': round(val, 3),
                                'year': 'unbekannt'
                            }

            return parsed
        except Exception as e:
            logger.error(f"Parse Fehler: {e}"); return None

class MQTTPublisher:
    def __init__(self, host, port, username, password, topic_prefix):
        self.host, self.port, self.topic_prefix = host, port, topic_prefix
        # Update auf Callback API Version 2
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="digimeto-bridge")
        self.connected = False
        if username and password: self.client.username_pw_set(username, password)
        # Callback für VERSION2 angepasst
        self.client.on_connect = self._on_connect

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.connected = True
        else:
            logger.error(f"MQTT Verbindungsfehler: {reason_code}")

    def connect(self):
        try:
            self.client.connect(self.host, self.port, 60)
            self.client.loop_start()
            for _ in range(50):
                if self.connected: return True
                time.sleep(0.1)
            return False
        except: return False

    def publish_data(self, data):
        if not self.connected and not self.connect(): return False
        try:
            self.client.publish(f"{self.topic_prefix}/data", json.dumps(data), retain=True)
            for sec in ['consumption', 'meter']:
                for k, v in data.get(sec, {}).items():
                    self.client.publish(f"{self.topic_prefix}/{sec}/{k}", str(v), retain=True)
            # Publiziere Tage und Monate
            for p in ['days', 'months']:
                for k, v in data.get('history', {}).get(p, {}).items():
                    self.client.publish(f"{self.topic_prefix}/history/{p}/{k}", str(v), retain=True)
            # Publiziere Jahre (extrahiere Wert aus Dict)
            for k, v_dict in data.get('history', {}).get('years', {}).items():
                if isinstance(v_dict, dict):
                    self.client.publish(f"{self.topic_prefix}/history/years/{k}", str(v_dict['value']), retain=True)
                else:
                    self.client.publish(f"{self.topic_prefix}/history/years/{k}", str(v_dict), retain=True)
            self.publish_discovery_config(data)
            return True
        except Exception as e:
            logger.error(f"MQTT Publish Fehler: {e}"); return False

    def publish_discovery_config(self, data):
        try:
            now = datetime.now()
            dev = {"identifiers": ["digimeto"], "name": "Digimeto Zähler", "manufacturer": "Digimeto"}
            wt = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            mn = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]

            metrics = {
                "today": ["Verbrauch Heute", "kWh", "energy", "total_increasing"],
                "current_year": ["Verbrauch Aktuelles Jahr", "kWh", "energy", "total_increasing"],
                "maloId": ["Marktlokation ID", None, None, None],
                "metpoint": ["Messstellenbezeichnung", None, None, None],
                "mq": ["Zähler OBIS Code", None, None, None]
            }
            
            for k, info in metrics.items():
                t = "meter" if k in ["maloId", "metpoint", "mq"] else "consumption"
                c = {"name": info[0], "object_id": f"digimeto_{k}", "unique_id": f"dg_{k}", "state_topic": f"{self.topic_prefix}/{t}/{k}", "device": dev}
                if info[1]: c["unit_of_measurement"] = info[1]
                if info[2]: c["device_class"] = info[2]
                if info[3]: c["state_class"] = info[3]
                self.client.publish(f"homeassistant/sensor/digimeto/{k}/config", json.dumps(c), retain=True)

            for i in range(1, 8):
                d_t = now - timedelta(days=i)
                c = {"name": f"Verbrauch {wt[d_t.weekday()]} ({d_t.strftime('%d.%m.')})", "object_id": f"digimeto_day_{i}", "unique_id": f"dg_day_{i}", "state_topic": f"{self.topic_prefix}/history/days/day_{i}", "unit_of_measurement": "kWh", "device_class": "energy", "state_class": "measurement", "device": dev}
                self.client.publish(f"homeassistant/sensor/digimeto/day_{i}/config", json.dumps(c), retain=True)

            for i in range(1, 14):
                m_t = now.replace(day=1) - timedelta(days=i*30)
                c = {"name": f"Verbrauch {mn[m_t.month-1]} {m_t.year}", "object_id": f"digimeto_mon_{i}", "unique_id": f"dg_mon_{i}", "state_topic": f"{self.topic_prefix}/history/months/month_{i}", "unit_of_measurement": "kWh", "device_class": "energy", "state_class": "measurement", "device": dev}
                self.client.publish(f"homeassistant/sensor/digimeto/mon_{i}/config", json.dumps(c), retain=True)
            
            # Letzte 3 Jahre - FESTE Entitäten mit dynamischen Namen aus den Daten
            years_data = data.get('history', {}).get('years', {})
            for year_num in range(1, 4):  # year_1, year_2, year_3
                year_key = f'year_{year_num}'
                year_info = years_data.get(year_key, {})
                
                # Extrahiere Jahr für Display-Name
                if isinstance(year_info, dict):
                    year_str = year_info.get('year', f'Jahr -{year_num-1}')
                else:
                    year_str = f'Jahr -{year_num-1}'
                
                # Jahr 1 = aktuelles/letztes, Jahr 2 = vorletztes, etc.
                c = {"name": f"Verbrauch Jahr {year_str}", "object_id": f"digimeto_year_{year_num}", "unique_id": f"dg_year_{year_num}", "state_topic": f"{self.topic_prefix}/history/years/{year_key}", "unit_of_measurement": "kWh", "device_class": "energy", "state_class": "total_increasing", "device": dev}
                self.client.publish(f"homeassistant/sensor/digimeto/year_{year_num}/config", json.dumps(c), retain=True)
        except Exception as e: logger.error(f"Discovery Fehler: {e}")

def main():
    logger.info("=== Digimeto MQTT Bridge gestartet ===")
    api = DigimetoAPI(DIGIMETO_USERNAME, DIGIMETO_PASSWORD)
    mqtt_p = MQTTPublisher(MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_TOPIC_PREFIX)
    
    logger.info(f"Verbinde mit MQTT Broker {MQTT_HOST}:{MQTT_PORT}...")
    if not mqtt_p.connect(): 
        logger.error("MQTT Verbindung fehlgeschlagen!")
        sys.exit(1)
    logger.info("MQTT verbunden")
    
    logger.info(f"Update-Intervall: {UPDATE_INTERVAL} Sekunden")
    
    while True:
        data = api.get_meter_data()
        if data: 
            mqtt_p.publish_data(data)
            logger.info("Daten an MQTT publiziert")
        else:
            logger.warning("Keine Daten empfangen")
        
        logger.info(f"Nächstes Update in {UPDATE_INTERVAL} Sekunden...")
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    main()

