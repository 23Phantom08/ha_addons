#!/usr/bin/env bash
set -e

CONFIG_PATH="/data/options.json"

echo "-------------------------------------------------------"
echo " Starte Digimeto Customer Portal (Playwright Edition)"
echo "-------------------------------------------------------"

# Lese Konfiguration aus Home Assistant Add-on Optionen
export DIGIMETO_USERNAME=$(jq --raw-output '.digimeto_username // empty' $CONFIG_PATH)
export DIGIMETO_PASSWORD=$(jq --raw-output '.digimeto_password // empty' $CONFIG_PATH)
export MQTT_HOST=$(jq --raw-output '.mqtt_host // "core-mosquitto"' $CONFIG_PATH)
export MQTT_PORT=$(jq --raw-output '.mqtt_port // 1883' $CONFIG_PATH)
export MQTT_USERNAME=$(jq --raw-output '.mqtt_username // empty' $CONFIG_PATH)
export MQTT_PASSWORD=$(jq --raw-output '.mqtt_password // empty' $CONFIG_PATH)
export MQTT_TOPIC_PREFIX=$(jq --raw-output '.mqtt_topic_prefix // "digimeto"' $CONFIG_PATH)
export UPDATE_INTERVAL=$(jq --raw-output '.update_interval // 3600' $CONFIG_PATH)
export LOG_LEVEL=$(jq --raw-output '.log_level // "info"' $CONFIG_PATH)

# Wechsle in /data, damit die Datei digimeto_auth_state.json 
# einen Reboot des Containers überlebt (Persistenz)
cd /data

echo "Verbindung zu MQTT: ${MQTT_HOST}:${MQTT_PORT}"
echo "Abrufintervall: ${UPDATE_INTERVAL} Sekunden"
echo "Log Level: ${LOG_LEVEL}"

# Starte das Python-Skript
exec python3 /digimeto_mqtt.py

