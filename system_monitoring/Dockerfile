ARG BUILD_FROM=ghcr.io/hassio-addons/base:15.0.6
FROM $BUILD_FROM

# Abhängigkeiten
RUN apk add --no-cache nodejs npm curl

WORKDIR /app

# App installieren
COPY rootfs/app/package.json ./
RUN npm install --production
COPY rootfs/app/ /app/

# Script an den S6-Ort kopieren
# WICHTIG: Der Ordnername bestimmt den Servicenamen
COPY rootfs/etc/services.d/system_monitor/run /etc/services.d/system_monitor/run
RUN chmod a+x /etc/services.d/system_monitor/run

# KEIN CMD ODER ENTRYPOINT HIER!

