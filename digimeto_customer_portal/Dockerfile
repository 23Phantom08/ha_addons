# WICHTIG: Nutze slim (Debian), nicht alpine für Playwright Support
FROM python:3.11-slim

# System-Abhängigkeiten für Playwright/Chromium installieren
RUN apt-get update && apt-get install -y --no-install-recommends \
    jq \
    bash \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Python-Pakete installieren
RUN pip3 install --no-cache-dir \
    requests \
    paho-mqtt \
    playwright

# Playwright Browser-Binaries und deren System-Abhängigkeiten
RUN playwright install chromium
RUN playwright install-deps chromium

# Skripte kopieren
COPY run.sh /
COPY digimeto_mqtt.py /

# Ausführungsrechte setzen
RUN chmod a+x /run.sh

# Startbefehl via run.sh
CMD [ "/run.sh" ]

