/**
 * INGRESS & API FETCH LOGIK
 * Nutzt den relativen Pfad, der durch den <base>-Tag in der index.html
 * für Home Assistant Ingress definiert wurde.
 */
const apiFetch = async (endpoint) => {
    try {
        const response = await fetch(`api/${endpoint}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (e) {
        console.error(`Fehler bei Endpunkt ${endpoint}:`, e);
        const el = document.getElementById(endpoint);
        if (el) el.innerText = "Err";
    }
};

// Tab-Navigation
function showTab(tabName, event) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    
    const targetTab = document.getElementById(tabName);
    if (targetTab) targetTab.classList.add('active');
    
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }
    
    // Daten beim Tab-Wechsel sofort aktualisieren
    if(tabName === 'addons') updateAddons();
    if(tabName === 'integrations') updateIntegrations();
    if(tabName === 'automations') updateAutomations();
}

// ============ UPDATE FUNKTIONEN ============

async function updateDevice() {
    const data = await apiFetch('device');
    if (data) {
        const deviceEl = document.getElementById('deviceInfo');
        if (deviceEl) deviceEl.innerText = `${data.icon || '📱'} ${data.device} (${data.ram}GB RAM)`;
    }
}

async function updateStats() {
    const data = await apiFetch('stats');
    if (data) {
        if (document.getElementById('cpu')) document.getElementById('cpu').innerText = data.cpu.toFixed(1) + ' %';
        if (document.getElementById('ram')) document.getElementById('ram').innerText = `${Math.round(data.ram)} / ${Math.round(data.ramTotal)} MB`;
        if (document.getElementById('uptime')) {
            const h = Math.floor(data.uptime / 3600);
            const m = Math.floor((data.uptime % 3600) / 60);
            document.getElementById('uptime').innerText = `${h}h ${m}m`;
        }
        if (document.getElementById('time')) document.getElementById('time').innerText = data.timestamp;

        // Temperatur nachladen
        const thermal = await apiFetch('thermal');
        if (thermal && document.getElementById('temp')) {
            const tempEl = document.getElementById('temp');
            tempEl.innerText = thermal.temp + " °C";
            const t = parseFloat(thermal.temp);
            tempEl.style.color = t > 70 ? "#ff3333" : (t > 60 ? "#ff9800" : "#00eaff");
        }
    }
}

async function updateHealth() {
    const data = await apiFetch('health');
    if (data) {
        if (document.getElementById('healthScore')) document.getElementById('healthScore').innerText = data.score;
        if (document.getElementById('healthStatus')) document.getElementById('healthStatus').innerText = data.status;
        const box = document.getElementById('healthStatusBox');
        if (box) {
            const colors = { 'Healthy': '#00eaff', 'Stressed': '#ff9800', 'Critical': '#ff3333' };
            box.style.borderColor = colors[data.status] || '#00eaff';
        }
    }
}

async function updateDisk() {
    const data = await apiFetch('disk');
    if (data && document.getElementById('disk')) {
        // Nutzt jetzt das formatierte Feld vom Server: "X GB (Y GB)"
        document.getElementById('disk').innerText = data.formatted || `${data.used} GB (${data.total} GB)`;
    }
}

async function updateNetwork() {
    const data = await apiFetch('network');
    if (data) {
        if (document.getElementById('network')) document.getElementById('network').innerText = data.status || "Verbunden";
        if (document.getElementById('networkIp')) document.getElementById('networkIp').innerText = data.ip;
    }
}

async function updateAddons() {
    const data = await apiFetch('addons');
    if (data) {
        document.getElementById('addonTotal').innerText = data.total;
        document.getElementById('addonRunning').innerText = data.running;
        const list = document.getElementById('addonsList');
        
        if (list && data.running_list) {
            list.innerHTML = data.running_list.map(entry => {
                // Wir prüfen, ob das "Aktiv"-Label vom Server im Text steckt
                const isRunning = entry.includes(': Aktiv');

                return `
                    <div class="addon-item ${isRunning ? 'addon-started' : 'addon-stopped'}">
                        <div class="addon-info">
                            <span class="addon-name">${entry}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }
    }
}

async function updateIntegrations() {
    const data = await apiFetch('integrations');
    if (data) {
        document.getElementById('integrationTotal').innerText = data.okCount;
        document.getElementById('integrationOK').innerText = data.okCount;
        const list = document.getElementById('integrationsList');
        
        if (list && data.list) {
            // Wir nehmen den fertigen String (🧩 Name) direkt vom Server
            list.innerHTML = data.list.map(title => `
                <div class="addon-item addon-started">
                    <div class="addon-info">
                        <span class="addon-name">${title}</span>
                    </div>
                </div>
            `).join('');
        }
    }
}

async function updateAutomations() {
    const data = await apiFetch('automations');
    if (data) {
        document.getElementById('automationTotal').innerText = data.total;
        document.getElementById('automationActive').innerText = data.active;
        document.getElementById('automationInactive').innerText = data.inactive;
        const list = document.getElementById('automationsList');
        
        if (list && data.active_list) {
            // Wir nehmen den String 1:1 so, wie der Server ihn liefert
            list.innerHTML = data.active_list.map(entry => {
                const isActive = entry.includes('Aktiv');

                return `
                    <div class="addon-item ${isActive ? 'addon-started' : 'addon-stopped'}">
                        <div class="addon-info">
                            <span class="addon-name">${entry}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }
    }
}

async function updateHAVersion() {
    const data = await apiFetch('haversion');
    if (data && document.getElementById('haVersion')) {
        document.getElementById('haVersion').innerText = data.version;
    }
}

async function updateUpdates() {
    const data = await apiFetch('updates');
    if (data && document.getElementById('updatesCount')) {
        document.getElementById('updatesCount').innerText = `${data.addons} Updates`;
    }
}

// Initialisierung beim Laden der Seite
document.addEventListener('DOMContentLoaded', () => {
    updateDevice();
    updateStats();
    updateHealth();
    updateDisk();
    updateNetwork();
    updateAddons();
    updateHAVersion();
    updateUpdates();
    
    // Live-Update Intervall (alle 5 Sekunden)
    setInterval(() => {
        updateStats();
        updateHealth();
        updateDisk();
        updateNetwork();
        
        // Listen nur aktualisieren, wenn der jeweilige Tab sichtbar ist
        if(document.getElementById('addons').classList.contains('active')) updateAddons();
        if(document.getElementById('integrations').classList.contains('active')) updateIntegrations();
        if(document.getElementById('automations').classList.contains('active')) updateAutomations();
    }, 5000);
});

