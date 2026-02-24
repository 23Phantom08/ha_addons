const os = require('os');
const { exec } = require('child_process');
const mqtt = require('mqtt');
const fs = require('fs');

// ============ 1. VARIABLEN & CONFIG ============

let mqttClient = null;
let mqttEnabled = false;
let mqttConfig = {
    broker: process.env.MQTT_BROKER || 'homeassistant',
    port: parseInt(process.env.MQTT_PORT || 1883),
    user: process.env.MQTT_USER || '',
    password: process.env.MQTT_PASSWORD || '',
    topicPrefix: process.env.MQTT_TOPIC_PREFIX || 'homeassistant/sensor/system_monitor',
    updateInterval: parseInt(process.env.UPDATE_INTERVAL || 5)
};

// ============ 2. HILFSFUNKTIONEN ============

function getGermanTime() {
    const now = new Date();
    const d = String(now.getDate()).padStart(2, '0');
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const y = now.getFullYear();
    const h = String(now.getHours()).padStart(2, '0');
    const min = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    return `${d}.${m}.${y}, ${h}:${min}:${s}`;
}

function log(msg) { console.log(`[${getGermanTime()}] ${msg}`); }

function getLocalIP() {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
        for (const iface of interfaces[name]) {
            if (iface.family === 'IPv4' && !iface.internal) return iface.address;
        }
    }
    return '127.0.0.1';
}

function detectDevice() {
    const cpus = os.cpus() || [];
    const model = cpus.length > 0 ? cpus[0].model : "Unbekannt";
    const ramGB = Math.round(os.totalmem() / (1024 ** 3));
    const arch = os.arch();
    let deviceName = "Home Assistant Host", icon = "🖥️";

    const isVM = model.includes('KVM') || model.includes('Virtual') || model.includes('VMware') || model.includes('QEMU');

    if (isVM) {
        deviceName = `Virtuelle Maschine (VM) (${ramGB}GB)`;
        icon = "🗄️";
    } else if (arch.includes('arm') || model.includes('Cortex') || model.includes('BCM') || arch.includes('aarch64')) {
        icon = "🍓";
        if (model.includes('Cortex-A76')) deviceName = `Raspberry Pi 5 (${ramGB}GB)`;
        else if (model.includes('Cortex-A72')) deviceName = `Raspberry Pi 4 (${ramGB}GB)`;
        else deviceName = `Raspberry Pi (${ramGB}GB)`;
    } else if (model.includes('Intel') || model.includes('AMD')) {
        deviceName = `Mini PC / x86 (${ramGB}GB)`;
        icon = "💻";
    }
    return { device: deviceName, icon: icon, ram: ramGB, arch: arch, cores: cpus.length };
}

let currentCpuUsage = 0;

// Diese Funktion läuft im Hintergrund und misst die Ticks (Allrounder für x86 & ARM)
function monitorCpuUsage() {
    const stats1 = os.cpus();
    setTimeout(() => {
        const stats2 = os.cpus();
        let totalIdle = 0, totalTick = 0;

        for (let i = 0; i < stats1.length; i++) {
            const cpu1 = stats1[i].times, cpu2 = stats2[i].times;
            totalIdle += cpu2.idle - cpu1.idle;
            totalTick += (cpu2.user + cpu2.nice + cpu2.sys + cpu2.irq + cpu2.idle) - 
                         (cpu1.user + cpu1.nice + cpu1.sys + cpu1.irq + cpu1.idle);
        }
        
        if (totalTick > 0) {
            currentCpuUsage = parseFloat(((1 - totalIdle / totalTick) * 100).toFixed(1));
        }
        monitorCpuUsage(); // Nächste Messung starten
    }, 1000);
}
monitorCpuUsage(); // Sofort beim Start aktivieren

// ============ 3. HARDWARE ABFRAGEN ============

function getCPUFreq(callback) {
    // 1. Pfad für Mini-PCs (x86 / Intel / AMD)
    const x86Path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq";
    // 2. Pfad für Raspberry Pi (ARM)
    const piPath = "/sys/class/thermal/cooling_device0/cur_state"; 
    // Alternativer Pi-Pfad (zuverlässiger für die echte Taktung):
    const piFreqPath = "/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq";

    let freq = null;

    try {
        if (fs.existsSync(piFreqPath)) {
            // Raspberry Pi liefert kHz -> / 1000000 für GHz
            freq = fs.readFileSync(piFreqPath, 'utf8').trim();
            return callback((parseInt(freq) / 1000000).toFixed(2));
        } else if (fs.existsSync(x86Path)) {
            // Mini-PC liefert oft kHz -> / 1000000 für GHz
            freq = fs.readFileSync(x86Path, 'utf8').trim();
            // Sicherheitsscheck: Wenn der Wert > 10000 ist, sind es kHz
            let val = parseInt(freq);
            return callback((val > 10000 ? val / 1000000 : val / 1000).toFixed(2));
        }
    } catch (e) {}

    // 3. Fallback: vcgencmd (Speziell für Raspberry Pi OS)
    // Das ist die genaueste Methode auf dem Pi
    exec("vcgencmd measure_clock arm", (err, stdout) => {
        if (!err && stdout && stdout.includes('=')) {
            const rawHz = stdout.split('=')[1];
            // vcgencmd liefert Hz -> / 1000000000 für GHz
            return callback((parseInt(rawHz) / 1000000000).toFixed(2));
        }

        // 4. Letzter Fallback: /proc/cpuinfo (für Mini-PC)
        exec("grep -m 1 'cpu MHz' /proc/cpuinfo | awk '{print $NF}'", (err, stdout) => {
            if (!err && stdout && stdout.trim()) {
                return callback((parseFloat(stdout.replace(',', '.')) / 1000).toFixed(2));
            }
            callback("0.00");
        });
    });
}

function getThermalData(callback) {
    
    const corePaths = [
        "/sys/class/hwmon/hwmon1/temp1_input", // Mini-PC Kern 1
        "/sys/class/hwmon/hwmon1/temp2_input", // Mini-PC Kern 2
        "/sys/class/hwmon/hwmon1/temp3_input", // Mini-PC Kern 3
        "/sys/class/hwmon/hwmon1/temp4_input", // Mini-PC Kern 4
        "/sys/class/hwmon/hwmon1/temp5_input", // Mini-PC Kern 5
        "/sys/class/hwmon/hwmon0/temp1_input", // Raspberry Pi (aus deinem Screenshot)
        "/sys/class/thermal/thermal_zone0/temp" // Allgemeiner Fallback
    ];

    let totalTemp = 0;
    let count = 0;

    for (const p of corePaths) {
        if (fs.existsSync(p)) {
            try {
                const raw = fs.readFileSync(p, 'utf8').trim();
                const val = parseInt(raw) / 1000;
                if (val > 0 && val < 110) {
                    totalTemp += val;
                    count++;
                }
            } catch (e) { }
        }
    }

    if (count > 0) {
        return callback({ temp: (totalTemp / count).toFixed(1) });
    }

    // Falls oben nichts gefunden wurde, vcgencmd (nur falls 'exec' oben deklariert ist)
    if (typeof exec === 'function') {
        exec("vcgencmd measure_temp 2>/dev/null", (err, stdout) => {
            if (!err && stdout) {
                const match = stdout.match(/temp=([\d.]+)/);
                if (match) return callback({ temp: parseFloat(match[1]).toFixed(1) });
            }
            callback({ temp: "N/A" });
        });
    } else {
        callback({ temp: "N/A" });
    }
}

function getSystemStats() {
    const usedMB = Math.round((os.totalmem() - os.freemem()) / (1024 * 1024));
    const totalMB = Math.round(os.totalmem() / (1024 * 1024));
    
    return { 
        cpu: currentCpuUsage, // Jetzt die echte, aktuelle Auslastung (Allrounder)
        ramFormatted: `${usedMB} MB (${totalMB} MB)`, 
        uptime: parseInt(os.uptime()) 
    };
}

// ============ 4. DISK & NETWORK ============

function getDiskSpace(callback) {
    exec("df -BG / | tail -1 | awk '{print $3 \" \" $2}'", (err, stdout) => {
        if (err || !stdout) return callback({ formatted: "N/A" });
        const parts = stdout.trim().split(/\s+/);
        const used = parseInt(parts[0]);
        const total = parseInt(parts[1]);
        callback({ 
            formatted: `${used} GB (${total} GB)`, 
            used: used, 
            total: total, 
            percent: Math.round((used / total) * 100) 
        });
    });
}

function getDiskType(callback) {
    const paths = [
        { p: '/sys/class/block/mmcblk0', t: 'MicroSD Karte', i: '💾', n: '/device/name' },
        { p: '/sys/class/block/nvme0n1', t: 'NVMe SSD', i: '⚡', n: '/device/model' },
        { p: '/sys/class/block/sda', t: 'SATA SSD/Disk', i: '💽', n: '/device/model' }
    ];

    for (const d of paths) {
        if (fs.existsSync(d.p)) {
            let model = "Generic";
            try {
                if (fs.existsSync(d.p + d.n)) {
                    model = fs.readFileSync(d.p + d.n, 'utf8').trim();
                }
            } catch (e) {}
            return callback({ display: `${d.i} ${d.t} (${model})` });
        }
    }

    exec("lsblk -dno NAME,MODEL | grep -v 'loop' | head -n 1", (err, stdout) => {
        if (!err && stdout.trim()) {
            return callback({ display: `💽 Disk (${stdout.trim()})` });
        }
        callback({ display: "💽 System SSD/Disk" });
    });
}

let lastIO = { time: Date.now(), read: 0, write: 0, drive: null };
function getDiskIO(callback) {
    if (!lastIO.drive) {
        const drives = ['nvme0n1', 'mmcblk0', 'sda', 'sdb'];
        lastIO.drive = drives.find(d => fs.existsSync(`/sys/class/block/${d}`)) || 'sda';
    }
    exec(`grep -w "${lastIO.drive}" /proc/diskstats`, (err, stdout) => {
        if (err || !stdout) return callback({ formatted: "N/A" });
        const parts = stdout.trim().split(/\s+/).filter(Boolean);
        const currentRead = parseInt(parts[5]); 
        const currentWrite = parseInt(parts[9]);
        const currentTime = Date.now();
        const timeDiff = (currentTime - lastIO.time) / 1000;

        if (timeDiff > 0 && lastIO.read > 0) {
            let rKB = ((currentRead - lastIO.read) * 0.5 / timeDiff);
            let wKB = ((currentWrite - lastIO.write) * 0.5 / timeDiff);

            const fmt = (kb) => {
                if (kb >= 1024) return `${(kb / 1024).toFixed(2)} MB/s`;
                return `${kb.toFixed(1)} KB/s`;
            };

            callback({ formatted: `R: ${fmt(rKB)} | W: ${fmt(wKB)}` });
        }
        lastIO = { time: currentTime, read: currentRead, write: currentWrite, drive: lastIO.drive };
    });
}

let lastNet = { time: Date.now(), rx: 0, tx: 0, interface: null };
function getNetworkSpeed(callback) {
    const findInt = "ip route | grep default | awk '{print $5}' | head -n 1";
    exec(lastNet.interface ? `cat /proc/net/dev | grep "${lastNet.interface}"` : findInt, (err, stdout) => {
        if (err || !stdout) return callback({ formatted: "0 KB/s" });
        if (!lastNet.interface) { lastNet.interface = stdout.trim(); return; }
        
        const parts = stdout.trim().split(/\s+/).filter(Boolean);
        const rxIdx = stdout.includes(':') ? 0 : 1;
        const rx = parseInt(parts[rxIdx].split(':').pop() || parts[rxIdx+1]);
        const tx = parseInt(parts[rxIdx+8]);
        const timeDiff = (Date.now() - lastNet.time) / 1000;

        if (timeDiff > 0 && lastNet.rx > 0) {
            const rxKB = (rx - lastNet.rx) / 1024 / timeDiff;
            const txKB = (tx - lastNet.tx) / 1024 / timeDiff;
            const fmt = (v) => v >= 1024 ? `${(v/1024).toFixed(2)} MB/s` : `${v.toFixed(1)} KB/s`;
            callback({ formatted: `⬇️ ${fmt(rxKB)} | ⬆️ ${fmt(txKB)}` });
        }
        lastNet = { time: Date.now(), rx, tx, interface: lastNet.interface };
    });
}

// ============ 5. RESTART TRACKING ============

const statusFilePath = '/data/system_health.json';

function trackRestartReason() {
    const currentSystemUptime = os.uptime();
    let data = { history: [], last_heartbeat: { timestamp: Date.now(), uptime: 0 } };
    let currentReason = "Erster Start / Initialisiert";

    if (fs.existsSync(statusFilePath)) {
        try {
            data = JSON.parse(fs.readFileSync(statusFilePath, 'utf8'));
            const lastState = data.last_heartbeat;
            const timeDiff = (Date.now() - lastState.timestamp) / 1000;

            // Logik: War die Pause länger als 90 Sekunden?
            if (timeDiff > 90) {
                // Wenn die PC-Uptime kleiner ist als beim letzten Check -> Strom war weg
                if (currentSystemUptime < lastState.uptime) {
                    currentReason = "Stromausfall / Hard Reset";
                } else {
                    // PC lief durch, nur Add-on/HA war weg -> Update oder Crash
                    currentReason = "Geplanter Neustart / Update";
                }
            } else {
                currentReason = "Manueller Service-Restart";
            }
        } catch (e) {
            currentReason = "Protokoll initialisiert";
        }
    }

    // Hier nutzen wir deine eigene Funktion für das Format
    const newEntry = `${getGermanTime()}: ${currentReason}`;
    data.history = [newEntry, ...(data.history || [])].slice(0, 10);

    // Heartbeat alle 30 Sekunden wegschreiben
    setInterval(() => {
        data.last_heartbeat = { 
            timestamp: Date.now(), 
            uptime: os.uptime() 
        };
        try {
            fs.writeFileSync(statusFilePath, JSON.stringify(data));
        } catch (e) {}
    }, 30000);

    return { current: currentReason, history: data.history };
}

const restartData = trackRestartReason();

// ============ 6. SUPERVISOR API ============

async function getCoreVersion(callback) {
    const token = process.env.SUPERVISOR_TOKEN;
    try {
        const response = await fetch("http://supervisor/core/api/config", { 
            headers: { "Authorization": `Bearer ${token}` } 
        });
        const data = await response.json();
        const dev = detectDevice(); // Für den Device Type
        if (data && data.version) {
            callback({ 
                version: data.version, 
                device_display: `${dev.icon} ${dev.device}` 
            });
        }
    } catch (e) { callback({ version: "N/A", device_display: "Unbekannt" }); }
}

let isAddonFetching = false;

async function getAddonStatus(callback) {
    const token = process.env.SUPERVISOR_TOKEN;
    if (!token || isAddonFetching) return; 

    isAddonFetching = true;
    let totalCpu = 0;
    let totalRam = 0;

    try {
        const response = await fetch("http://supervisor/addons", { 
            headers: { "Authorization": `Bearer ${token}` },
            signal: AbortSignal.timeout(10000) // Erhöht auf 10s für viele Add-ons
        });

        if (!response.ok) {
            isAddonFetching = false;
            return;
        }

        const res = await response.json();
        if (res.result === "ok") {
            const addons = res.data.addons;
            
            const fullList = await Promise.all(addons.map(async (a) => {
                const isRunning = a.state === 'started';
                let statsInfo = "";
                
                if (isRunning) {
                    try {
                        // Stats Abruf mit etwas mehr Puffer (3s)
                        const sRes = await fetch(`http://supervisor/addons/${a.slug}/stats`, { 
                            headers: { "Authorization": `Bearer ${token}` },
                            signal: AbortSignal.timeout(3000) 
                        });
                        const s = await sRes.json();
                        
                        if (s.result === "ok" && s.data) {
                            // Deine exakte Logik
                            const cpuVal = s.data.cpu_percent || 0;
                            const ramVal = s.data.memory_usage || 0;
                            
                            const cpu = cpuVal.toFixed(1);
                            const ram = (ramVal / (1024 * 1024)).toFixed(1);
                            
                            statsInfo = ` [CPU: ${cpu}%, RAM: ${ram}MB]`;
                            
                            totalCpu += cpuVal;
                            totalRam += (ramVal / (1024 * 1024));
                        } else {
                            statsInfo = " [Warten...]"; // API hat geantwortet, aber keine Daten geliefert
                        }
                    } catch (e) { 
                        statsInfo = " [Stats Fehler]"; // Timeout oder Supervisor beschäftigt
                    }
                }
                
                const icon = isRunning ? '✅' : '🛑';
                const statusLabel = isRunning ? 'Aktiv' : 'Gestoppt';
                const updateLabel = a.update_available ? ' 🚀 (Update verfügbar!)' : '';
                
                return `${icon} ${a.name}: ${statusLabel}${statsInfo}${updateLabel}`;
            }));

            fullList.sort((a, b) => a.localeCompare(b));

            const updateAvailableNames = addons
                .filter(a => a.update_available)
                .map(a => a.name);

            callback({
                total: addons.length,
                running: addons.filter(a => a.state === 'started').length,
                cpu_total: totalCpu.toFixed(1) + " %",
                ram_total: totalRam.toFixed(1) + " MB",
                updates_count: updateAvailableNames.length,
                updates_list: updateAvailableNames.length > 0 ? updateAvailableNames : ["Keine Updates verfügbar"],
                running_list: fullList
            });
        }
    } catch (e) {
        // Fehler silent
    } finally {
        isAddonFetching = false;
    }
}

async function getIntegrationStatus(callback) {
    const token = process.env.SUPERVISOR_TOKEN;
    try {
        const response = await fetch("http://supervisor/core/api/config", { headers: { "Authorization": `Bearer ${token}` } });
        const data = await response.json();
        if (data && data.components) {
            const systemKeywords = ['analytics', 'application_credentials', 'assist_pipeline', 'assist_satellite', 'automation', 'ai_task', 'alarm_control_panel', 'blueprint', 'bluetooth_adapters', 'button', 'camera', 'cloud', 'co2signal', 'conversation', 'counter', 'cover', 'default_config', 'device_automation', 'device_tracker', 'diagnostics', 'dhcp', 'event', 'fan', 'ffmpeg', 'file', 'file_upload', 'google_translate', 'go2rtc', 'hardware', 'hassio', 'history', 'homeassistant_alerts', 'humidifier', 'image', 'image_upload', 'input_', 'intent', 'labs', 'light', 'lock', 'logbook', 'logger', 'lovelace', 'media_player', 'media_source', 'my', 'network', 'notify', 'number', 'onboarding', 'panel_custom', 'persistent_notification', 'recorder', 'remote', 'repairs', 'scene', 'schedule', 'script', 'search', 'select', 'sensor', 'siren', 'ssdp', 'stream', 'stt', 'switch', 'system_health', 'system_log', 'tag', 'template', 'text', 'time', 'timer', 'todo', 'trace', 'tts', 'update', 'usage_prediction', 'usb', 'utility_meter', 'vacuum', 'valve', 'wake_word', 'water_heater', 'web_rtc', 'webhook', 'websocket_api', 'weather', 'zeroconf', 'zone', 'person', 'binary_sensor', 'climate', 'config', 'energy', 'frontend', 'api', 'auth', 'http'];
            
            const filtered = data.components.filter(comp => {
                const isSystem = systemKeywords.some(keyword => comp.startsWith(keyword) || comp === keyword);
                return !comp.includes('.') && !isSystem;
            }).sort();

            // Hier fügen wir das Icon 🧩 vor jede Integration ein
            const list = filtered.map(domain => {
                const name = domain.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                return `🧩 ${name}`;
            });

            callback({ okCount: list.length, total: list.length, list: list });
        }
    } catch (e) { callback({ okCount: 0, list: [] }); }
}

let isFetching = false;
let initialDelayPassed = false;

async function getAutomations(callback) {
    // 1. Harte Sperre: Wenn gerade ein Abruf läuft, sofort abbrechen
    if (isFetching) return;

    // 2. Start-Verzögerung: In den ersten 60s nach Skriptstart gar nichts tun
    if (!initialDelayPassed) {
        setTimeout(() => { initialDelayPassed = true; }, 60000);
        return; 
    }

    isFetching = true;
    const token = process.env.SUPERVISOR_TOKEN;
    const url = "http://supervisor/core/api/states";

    try {
        const response = await fetch(url, { 
            headers: { "Authorization": `Bearer ${token}` },
            signal: AbortSignal.timeout(10000) // Timeout nach 10s, falls API hängt
        });

        if (!response.ok) {
            // Wir werfen keinen Error, sondern loggen nur still, um den Stacktrace klein zu halten
            if (response.status !== 502) {
                log(`HA API Status: ${response.status} (Noch im Startvorgang...)`);
            }
            isFetching = false;
            return;
        }

        const data = await response.json();
        const autos = data.filter(s => s.entity_id.startsWith('automation.'));
        
        const fullList = autos.map(a => {
            const name = a.attributes.friendly_name || a.entity_id;
            const isActive = a.state === 'on';
            return `${isActive ? '⚡' : '💤'} ${name}: ${isActive ? 'Aktiv' : 'Inaktiv'}`;
        }).sort((a, b) => a.localeCompare(b));

        callback({
            total: autos.length,
            active: autos.filter(a => a.state === 'on').length,
            inactive: autos.filter(a => a.state !== 'on').length,
            active_list: fullList 
        });

    } catch (e) {
        // Nur kritische Fehler loggen, keine Timeouts während des Boots
        if (e.name !== 'TimeoutError') {
            log(`Automationen Abruf pausiert: API nicht bereit.`);
        }
    } finally {
        // Sperre in jedem Fall wieder aufheben
        isFetching = false;
    }
}

async function getErrorLogs(callback) {
    try {
        const response = await fetch("http://supervisor/core/api/error_log", { 
            headers: { "Authorization": `Bearer ${process.env.SUPERVISOR_TOKEN}` } 
        });
        const text = await response.text();
        
        // Filtert Fehler UND kritische Warnungen
        const lines = text.split('\n');
        const relevantLogs = lines.filter(line => 
            line.includes(' ERROR ') || 
            line.includes(' CRITICAL ') || 
            line.includes(' WARNING ')
        );

        // Die letzten 10 Logs aufbereiten
        const lastTen = relevantLogs.slice(-10).reverse().map(line => {
            // Kürzt bekannte lange Pfade, um Platz für die echte Fehlermeldung zu schaffen
            let cleanLine = line.replace('/usr/src/homeassistant/homeassistant/', 'HA: ');
            
            // Falls die Zeile sehr lang ist, am Ende sauber abschneiden
            return cleanLine.length > 255 ? cleanLine.substring(0, 252) + "..." : cleanLine;
        });

        callback({ 
            count: relevantLogs.length, 
            list: lastTen.length > 0 ? lastTen : ["Keine kritischen Fehler im Log"]
        });
    } catch (e) { 
        callback({ count: 0, list: ["Fehler beim Abrufen der Logs"] }); 
    }
}

// ============ 7. MQTT DISCOVERY & PUBLISHING ============

function publishDiscovery() {
    if (!mqttClient || !mqttEnabled) return;
    const device = detectDevice();
    const devPayload = { identifiers: ["ha_system_monitor_mqtt"], name: "System Monitor", model: device.device, manufacturer: "NodeJS Monitor" };

    const sensors = [
        { id: "cpu", name: "CPU Load", unit: "%", icon: "mdi:speedometer", topic: "system_stats", val: "{{ value_json.cpu }}", state_class: "measurement" },
        { id: "ram", name: "RAM Usage", icon: "mdi:memory", topic: "system_stats", val: "{{ value_json.ramFormatted }}" },
        { id: "temp", name: "CPU Temperature", unit: "°C", icon: "mdi:thermometer", topic: "thermal", val: "{{ value_json.temp }}", state_class: "measurement", device_class: "temperature" },
        { id: "disk", name: "Storage Space", icon: "mdi:harddisk", topic: "disk", val: "{{ value_json.formatted }}", attr: true },
        { id: "disk_io", name: "Disk Activity", icon: "mdi:transfer", topic: "disk_io", val: "{{ value_json.formatted }}", attr: true },
        { id: "disk_type", name: "Storage Type", icon: "mdi:database", topic: "disk_info", val: "{{ value_json.display }}" },
        { id: "network", name: "Network Info", icon: "mdi:ip-network", topic: "network", val: "{{ value_json.ip }}", attr: true },
        { id: "network_speed", name: "Network Speed", icon: "mdi:swap-vertical", topic: "network_speed", val: "{{ value_json.formatted }}" },
        { id: "addons", name: "Add-ons", icon: "mdi:package-variant", topic: "addons", val: "{{ value_json.running }}", attr: true },
        { id: "integrations", name: "Integrations", icon: "mdi:puzzle", topic: "integrations", val: "{{ value_json.okCount }}", attr: true },
        { id: "automations", name: "Automations", icon: "mdi:robot", topic: "automations", val: "{{ value_json.active }}", attr: true },
        { id: "logs", name: "System Errors", icon: "mdi:alert-circle-outline", topic: "logs", val: "{{ value_json.count }}", attr: true },
        { id: "cpu_freq", name: "CPU Clock Speed", unit: "GHz", icon: "mdi:speedometer", topic: "cpu_info", val: "{{ value_json.freq }}", state_class: "measurement" },
        { id: "health", name: "Health Status", icon: "mdi:clock-alert", topic: "health", val: "{{ value_json.reason }}", attr: true },
        { id: "version", name: "HA Core Version", icon: "mdi:alpha-v-circle-outline", topic: "version", val: "{{ value_json.version }}" },
        { id: "device_name", name: "Device Type", icon: "mdi:monitor", topic: "version", val: "{{ value_json.device_display }}" }
    ];

    sensors.forEach(s => {
        const config = {
            name: s.name, unique_id: `ha_sys_mon_${s.id}`,
            state_topic: `${mqttConfig.topicPrefix}/${s.topic}`,
            value_template: s.val, icon: s.icon, device: devPayload,
            availability_topic: `${mqttConfig.topicPrefix}/status`
        };
        if (s.unit) config.unit_of_measurement = s.unit;
        if (s.attr) config.json_attributes_topic = `${mqttConfig.topicPrefix}/${s.topic}`;
        if (s.state_class) config.state_class = s.state_class;
        if (s.device_class) config.device_class = s.device_class;
        mqttClient.publish(`homeassistant/sensor/system_monitor/${s.id}/config`, JSON.stringify(config), { retain: true });
    });
    mqttClient.publish(`${mqttConfig.topicPrefix}/status`, "online", { retain: true });
}

function startMQTTPublishing() {
    setInterval(() => {
        if (!mqttEnabled || !mqttClient) return;

        // GRUPPE 1: ECHTZEIT (5s Takt)
        getCPUFreq(f => mqttClient.publish(`${mqttConfig.topicPrefix}/cpu_info`, JSON.stringify({ freq: f })));
        getThermalData(t => mqttClient.publish(`${mqttConfig.topicPrefix}/thermal`, JSON.stringify({ temp: t.temp })));
        mqttClient.publish(`${mqttConfig.topicPrefix}/system_stats`, JSON.stringify(getSystemStats()));

        // GRUPPE 2: STATUS & NETZWERK
        const dev = detectDevice(); 
        mqttClient.publish(`${mqttConfig.topicPrefix}/network`, JSON.stringify({ status: "Online", ip: getLocalIP() }));
        
        // --- ANPASSUNG HIER ---
        mqttClient.publish(`${mqttConfig.topicPrefix}/health`, JSON.stringify({ 
            reason: restartData.current, 
            history: restartData.history.join('\n') // Verbindet Einträge mit Zeilenumbruch für HA
        }));
        // -----------------------

        getNetworkSpeed(net => mqttClient.publish(`${mqttConfig.topicPrefix}/network_speed`, JSON.stringify(net)));
        getDiskIO(io => mqttClient.publish(`${mqttConfig.topicPrefix}/disk_io`, JSON.stringify(io)));

        // GRUPPE 3: HINTERGRUND (Träge Abfragen mit Listen-Attributen)
        setImmediate(() => {
            getDiskSpace(d => mqttClient.publish(`${mqttConfig.topicPrefix}/disk`, JSON.stringify(d)));
            getDiskType(info => mqttClient.publish(`${mqttConfig.topicPrefix}/disk_info`, JSON.stringify(info)));
            
            getAddonStatus(d => {
                mqttClient.publish(`${mqttConfig.topicPrefix}/addons`, JSON.stringify({ 
                    total: d.total,
                    running: d.running,
                    updates_count: d.updates_count,
                    updates_list: d.updates_list,
                    running_list: d.running_list 
                }));
            });

            getIntegrationStatus(d => {
                mqttClient.publish(`${mqttConfig.topicPrefix}/integrations`, JSON.stringify({ 
                    okCount: d.okCount, 
                    total: d.total, 
                    list: d.list 
                }));
            });

            getAutomations(d => {
                mqttClient.publish(`${mqttConfig.topicPrefix}/automations`, JSON.stringify({ 
                    total: d.total, 
                    active: d.active, 
                    inactive: d.inactive, 
                    active_list: d.active_list 
                }));
            });

            getErrorLogs(d => {
                mqttClient.publish(`${mqttConfig.topicPrefix}/logs`, JSON.stringify({ 
                    count: d.count, 
                    list: d.list 
                }));
            });
            
            getCoreVersion(v => {
                mqttClient.publish(`${mqttConfig.topicPrefix}/version`, JSON.stringify({ 
                    version: v.version, 
                    device_display: `${dev.icon} ${dev.device}` 
                }));
            });
        });
    }, mqttConfig.updateInterval * 1000);
}

function initMQTT() {
    const BLUE = '\x1b[1;34m';
    const GREEN = '\x1b[1;32m';
    const MAGENTA = '\x1b[1;35m';
    const BOLD = '\x1b[1m';
    const NC = '\x1b[0m';

    try {
        const dev = detectDevice();
        
        mqttClient = mqtt.connect(`mqtt://${mqttConfig.broker}:${mqttConfig.port}`, {
            username: mqttConfig.user, password: mqttConfig.password,
            clientId: 'ha-sys-mon-' + Math.random().toString(16).substr(2, 8)
        });

        mqttClient.on('connect', () => {
            mqttEnabled = true;
            
            getDiskType(disk => {
                // Deutsche Zeit im 24h-Format generieren (00:00:00)
                const startTime = new Date().toLocaleTimeString('de-DE', { 
                    hour12: false, 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit' 
                });

                console.log(`\n${BOLD}📡 NETWORK CONFIGURATION${NC}`);
                console.log(`   ${BLUE}Broker:${NC}      ${BOLD}${mqttConfig.broker}:${mqttConfig.port}${NC}`);
                console.log(`   ${BLUE}MQTT-Mode:${NC}   ${GREEN}ONLINE ✅${NC}`);
                
                console.log(`\n${BOLD}⚙️  SERVICE SETTINGS${NC}`);
                console.log(`   ${BLUE}Interval:${NC}    ${MAGENTA}${mqttConfig.updateInterval}s${NC}`);
                console.log(`   ${BLUE}Device:${NC}      ${dev.icon} ${dev.device}`);
                console.log(`   ${BLUE}Storage:${NC}     ${disk.display}`);
                
                console.log(`\n${BLUE}───────────────────────────────────────────────────────────${NC}`);
                console.log(` ${GREEN}✔ System Monitor successfully started at ${startTime}${NC}`);
                console.log(`${BLUE}───────────────────────────────────────────────────────────${NC}\n`);
                
                publishDiscovery();
                startMQTTPublishing();
            });
        });

        mqttClient.on('error', (err) => {
            console.log(`\n${MAGENTA}❌ MQTT Fehler: ${err.message}${NC}`);
        });
    } catch (e) { console.log(`\x1b[1;33m⚠️ Init Error: ${e.message}\x1b[0m`); }
}

initMQTT();

