// ==============================================================================
// TRAFFNODE V2 — DUAL-ENGINE HYBRID PASSIVE INCOME (PORT 8888)
// Zero-Dead-Controls • WCAG AA Contrast • Non-Destructive Dual-Pool
// ==============================================================================

let currentStatusData = null;
let pollTimer = null;
let activeFilter = 'all';
let currentLogNodeId = null;

// DOM ELEMENTS — HEADER & METRICS
const valServerIp = document.getElementById('val-server-ip');
const daemonStatusText = document.getElementById('daemon-status-text');
const statRunningNodes = document.getElementById('stat-running-nodes');
const statTotalNodes = document.getElementById('stat-total-nodes');
const statDualBalance = document.getElementById('stat-dual-balance');
const statCompDetail = document.getElementById('stat-comp-detail');
const statBandwidthTotal = document.getElementById('stat-bandwidth-total');
const statBandwidthSpeed = document.getElementById('stat-bandwidth-speed');
const statCpuRam = document.getElementById('stat-cpu-ram');
const statRamDetail = document.getElementById('stat-ram-detail');

// POOL STATUS COUNTERS
const cntSsRunning = document.getElementById('cnt-ss-running');
const cntSsTotal = document.getElementById('cnt-ss-total');
const lblSsStatus = document.getElementById('lbl-ss-status');
const cntPxRunning = document.getElementById('cnt-px-running');
const cntPxTotal = document.getElementById('cnt-px-total');
const lblPxStatus = document.getElementById('lbl-px-status');

// PROVIDER & CONFIG
const tagParseCount = document.getElementById('tag-parse-count');
const cfgToken = document.getElementById('cfg-token');
const btnSaveToken = document.getElementById('btn-save-token');

// SURFSHARK CONTROLS
const cfgSurfsharkKey = document.getElementById('cfg-surfshark-key');
const cfgSurfsharkRegion = document.getElementById('cfg-surfshark-region');
const cfgSurfsharkCount = document.getElementById('cfg-surfshark-count');
const cfgSurfsharkPort = document.getElementById('cfg-surfshark-port');
const cfgSurfsharkMode = document.getElementById('cfg-surfshark-mode');
const btnGenerateSurfshark = document.getElementById('btn-generate-surfshark');
const btnClearSurfshark = document.getElementById('btn-clear-surfshark');

// CUSTOM PROXIES CONTROLS
const proxiesTextarea = document.getElementById('proxies-textarea');
const cfgProxiesMode = document.getElementById('cfg-proxies-mode');
const lblProxyCountHint = document.getElementById('lbl-proxy-count-hint');
const btnSaveProxies = document.getElementById('btn-save-proxies');
const btnCheckProxies = document.getElementById('btn-check-proxies');
const btnClearProxies = document.getElementById('btn-clear-proxies');

// MASTER CONTROLS
const btnStartAll = document.getElementById('btn-start-all');
const btnStopAll = document.getElementById('btn-stop-all');
const btnStartSs = document.getElementById('btn-start-ss');
const btnStartPx = document.getElementById('btn-start-px');
const btnRestartAll = document.getElementById('btn-restart-all');
const btnStopSs = document.getElementById('btn-stop-ss');
const btnStopPx = document.getElementById('btn-stop-px');
const lblBtnTotalAll = document.getElementById('lbl-btn-total-all');
const lblBtnSsCount = document.getElementById('lbl-btn-ss-count');
const lblBtnPxCount = document.getElementById('lbl-btn-px-count');

const txtBtnStartAll = document.getElementById('txt-btn-start-all');
const txtBtnStopAll = document.getElementById('txt-btn-stop-all');
const txtBtnStartSs = document.getElementById('txt-btn-start-ss');
const txtBtnStartPx = document.getElementById('txt-btn-start-px');
const txtBtnRestartAll = document.getElementById('txt-btn-restart-all');
const txtBtnStopSs = document.getElementById('txt-btn-stop-ss');
const txtBtnStopPx = document.getElementById('txt-btn-stop-px');
const txtBtnGenSs = document.getElementById('txt-btn-gen-ss');
const txtBtnSavePx = document.getElementById('txt-btn-save-px');
const txtBtnCheckPx = document.getElementById('txt-btn-check-px');

// RESOURCE METERS
const barCpu = document.getElementById('bar-cpu');
const barRam = document.getElementById('bar-ram');
const txtCpu = document.getElementById('txt-cpu');
const txtRam = document.getElementById('txt-ram');

// TABLE, FILTER PILLS & SEARCH
const tableFilter = document.getElementById('table-filter');
const nodesTbody = document.getElementById('nodes-tbody');
const toastEl = document.getElementById('tn-toast');
const healthStatusText = document.getElementById('health-status-text');
const cntPillAll = document.getElementById('cnt-pill-all');
const cntPillSs = document.getElementById('cnt-pill-ss');
const cntPillPx = document.getElementById('cnt-pill-px');
const cntPillRunning = document.getElementById('cnt-pill-running');
const cntPillError = document.getElementById('cnt-pill-error');

// LOG MODAL
const logModal = document.getElementById('log-modal');
const logModalTitle = document.getElementById('log-modal-title');
const logModalBody = document.getElementById('log-modal-body');
const btnCloseModal = document.getElementById('btn-close-modal');
const btnRefreshLog = document.getElementById('btn-refresh-log');

// TAB SWITCHER
window.switchTab = function(tabName) {
    document.querySelectorAll('.tn-tab-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.tn-tab-content').forEach(c => c.classList.remove('active'));

    const btn = document.getElementById(`tab-btn-${tabName}`);
    const content = document.getElementById(`tab-content-${tabName}`);
    if (btn) {
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
    }
    if (content) {
        content.classList.add('active');
    }
};

// FORMAT HELPERS
function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatUptime(seconds) {
    if (!seconds || seconds <= 0) return '-';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

function showToast(msg, isError = false) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.style.borderColor = isError ? '#ef4444' : '#38bdf8';
    toastEl.style.color = isError ? '#fca5a5' : '#f8fafc';
    toastEl.style.display = 'block';
    clearTimeout(toastEl._timer);
    toastEl._timer = setTimeout(() => {
        toastEl.style.display = 'none';
    }, 4000);
}

// PROXY TEXTAREA HINT
function updateProxyLineCount() {
    if (!proxiesTextarea) return;
    const lines = proxiesTextarea.value.split('\n').filter(l => l.trim().length > 0 && !l.trim().startsWith('#'));
    if (lblProxyCountHint) {
        lblProxyCountHint.textContent = `${lines.length} proxy terdeteksi di form`;
    }
}
if (proxiesTextarea) {
    proxiesTextarea.addEventListener('input', updateProxyLineCount);
}

// FETCH SYSTEM STATUS
async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const data = await res.json();
        currentStatusData = data;
        renderDashboard(data);
    } catch (err) {
        console.error("Status fetch error:", err);
    }
}

// FETCH RAW PROXIES ON INITIAL LOAD
async function fetchRawProxies() {
    try {
        const res = await fetch('/api/proxies/raw');
        if (res.ok && proxiesTextarea && proxiesTextarea.value === "") {
            const txt = await res.text();
            proxiesTextarea.value = txt;
            updateProxyLineCount();
        }
    } catch (e) {}
}

// RENDER DASHBOARD & METRICS
function renderDashboard(data) {
    if (valServerIp) valServerIp.textContent = data.server_ip || '127.0.0.1';

    const cfg = data.config || {};
    if (cfgToken && document.activeElement !== cfgToken && cfg.traff_token) {
        cfgToken.value = cfg.traff_token;
    }
    if (cfgSurfsharkKey && document.activeElement !== cfgSurfsharkKey && cfg.surfshark_private_key) {
        cfgSurfsharkKey.value = cfg.surfshark_private_key;
    }
    if (cfgSurfsharkRegion && document.activeElement !== cfgSurfsharkRegion && cfg.surfshark_region) {
        cfgSurfsharkRegion.value = cfg.surfshark_region;
    }
    if (cfgSurfsharkCount && document.activeElement !== cfgSurfsharkCount && cfg.surfshark_node_count) {
        cfgSurfsharkCount.value = cfg.surfshark_node_count;
    }
    if (cfgSurfsharkPort && document.activeElement !== cfgSurfsharkPort && cfg.surfshark_start_port) {
        cfgSurfsharkPort.value = cfg.surfshark_start_port;
    }

    const m = data.metrics || {};
    const total = m.total_nodes || 0;
    const running = m.running_nodes || 0;
    const ssNodes = m.surfshark_nodes || 0;
    const ssRunning = m.surfshark_running || 0;
    const pxNodes = m.proxy_nodes || 0;
    const pxRunning = m.proxy_running || 0;

    // Top Cards
    if (statRunningNodes) {
        if (m.starting_nodes > 0 || m.is_starting_batch) {
            statRunningNodes.textContent = `${running} (+${m.starting_nodes || 0} starting...)`;
        } else {
            statRunningNodes.textContent = running;
        }
    }
    if (statTotalNodes) statTotalNodes.textContent = `${total} Total Nodes Terdaftar`;
    if (statDualBalance) statDualBalance.textContent = `${ssNodes} SS / ${pxNodes} PX`;
    if (statCompDetail) statCompDetail.textContent = `🦈 ${ssRunning}/${ssNodes} SS Active • 🌐 ${pxRunning}/${pxNodes} PX Active`;

    // Bandwidth
    const bw = m.bandwidth || {};
    if (statBandwidthTotal) {
        statBandwidthTotal.textContent = `${bw.formatted_in || '0 B'} ↓ / ${bw.formatted_out || '0 B'} ↑`;
    }
    if (statBandwidthSpeed) {
        statBandwidthSpeed.textContent = `${formatBytes(bw.speed_up_bps || 0)}/s Up • ${formatBytes(bw.speed_down_bps || 0)}/s Down`;
    }

    // Hardware Vitals
    const sys = data.system || {};
    if (statCpuRam) statCpuRam.textContent = `${sys.cpu_percent || 0}% CPU`;
    if (statRamDetail) statRamDetail.textContent = `RAM: ${sys.ram_used_mb || 0} MB / ${sys.ram_total_mb || 0} MB (${sys.ram_percent || 0}%)`;
    if (barCpu) barCpu.style.width = `${Math.min(100, sys.cpu_percent || 0)}%`;
    if (barRam) barRam.style.width = `${Math.min(100, sys.ram_percent || 0)}%`;
    if (txtCpu) txtCpu.textContent = `${sys.cpu_percent || 0}%`;
    if (txtRam) txtRam.textContent = `${sys.ram_percent || 0}%`;

    // Pool Boxes
    if (cntSsRunning) cntSsRunning.textContent = ssRunning;
    if (cntSsTotal) cntSsTotal.textContent = `/ ${ssNodes} Siap`;
    if (lblSsStatus) {
        if (ssRunning > 0) {
            lblSsStatus.textContent = `Aktif Menghasilkan Bandwidth (${ssRunning} Node)`;
            lblSsStatus.style.color = '#22c55e';
        } else if (m.is_starting_batch && ssNodes > 0) {
            lblSsStatus.textContent = 'Memulai bertahap (pacing 0.6s)...';
            lblSsStatus.style.color = '#fbbf24';
        } else {
            lblSsStatus.textContent = ssNodes > 0 ? 'Siap Dijalankan' : 'Belum Ada Node';
            lblSsStatus.style.color = '#cbd5e1';
        }
    }

    if (cntPxRunning) cntPxRunning.textContent = pxRunning;
    if (cntPxTotal) cntPxTotal.textContent = `/ ${pxNodes} Siap`;
    if (lblPxStatus) {
        if (pxRunning > 0) {
            lblPxStatus.textContent = `Aktif Menghasilkan Bandwidth (${pxRunning} Node)`;
            lblPxStatus.style.color = '#22c55e';
        } else if (m.is_starting_batch && pxNodes > 0) {
            lblPxStatus.textContent = 'Memulai bertahap (pacing 0.6s)...';
            lblPxStatus.style.color = '#fbbf24';
        } else {
            lblPxStatus.textContent = pxNodes > 0 ? 'Siap Dijalankan' : 'Belum Ada Node';
            lblPxStatus.style.color = '#cbd5e1';
        }
    }

    // Buttons Count
    if (lblBtnTotalAll) lblBtnTotalAll.textContent = total;
    if (lblBtnSsCount) lblBtnSsCount.textContent = ssNodes;
    if (lblBtnPxCount) lblBtnPxCount.textContent = pxNodes;
    if (tagParseCount) tagParseCount.textContent = `${total} Node (SS: ${ssNodes}, PX: ${pxNodes})`;

    // Filter Pill Counters
    const allNodesList = data.nodes || [];
    const deadCount = allNodesList.filter(n => n.status === 'ERROR' || n.is_alive === false).length;
    if (cntPillAll) cntPillAll.textContent = allNodesList.length;
    if (cntPillSs) cntPillSs.textContent = ssNodes;
    if (cntPillPx) cntPillPx.textContent = pxNodes;
    if (cntPillRunning) cntPillRunning.textContent = running;
    if (cntPillError) cntPillError.textContent = deadCount;
    const cntPurgeError = document.getElementById('cnt-purge-error');
    if (cntPurgeError) cntPurgeError.textContent = deadCount;

    // Render Table
    renderTable(allNodesList);
}

// RENDER TABLE WITH REAL-TIME FILTERING
function renderTable(nodesList) {
    if (!nodesTbody) return;

    const searchTerm = (tableFilter ? tableFilter.value.trim().toLowerCase() : '');

    const filtered = nodesList.filter(n => {
        // Pill filter
        if (activeFilter === 'surfshark' && n.node_type !== 'surfshark') return false;
        if (activeFilter === 'proxy' && n.node_type !== 'proxy') return false;
        if (activeFilter === 'running' && n.status !== 'RUNNING' && n.status !== 'STARTING') return false;
        if (activeFilter === 'error' && (n.status !== 'ERROR' && n.is_alive !== false)) return false;

        // Search text
        if (searchTerm) {
            const idStr = String(n.id);
            const dev = (n.device_name || '').toLowerCase();
            const host = (n.host || '').toLowerCase();
            const country = (n.country || '').toLowerCase();
            const endpoint = (n.endpoint || '').toLowerCase();
            const type = (n.node_type || '').toLowerCase();
            const status = (n.status || '').toLowerCase();

            if (!idStr.includes(searchTerm) &&
                !dev.includes(searchTerm) &&
                !host.includes(searchTerm) &&
                !country.includes(searchTerm) &&
                !endpoint.includes(searchTerm) &&
                !type.includes(searchTerm) &&
                !status.includes(searchTerm)) {
                return false;
            }
        }
        return true;
    });

    if (filtered.length === 0) {
        nodesTbody.innerHTML = `
            <tr>
                <td colspan="10" class="tn-text-center tn-muted" style="padding: 24px;">
                    Tidak ada worker yang sesuai dengan filter '${activeFilter.toUpperCase()}'.
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    for (const node of filtered) {
        const isSS = (node.node_type === 'surfshark');
        const typeBadge = isSS
            ? `<span class="tn-badge tn-badge-surfshark">🦈 SURFSHARK</span>`
            : `<span class="tn-badge tn-badge-proxy">🌐 CUSTOM PROXY</span>`;

        let statusBadge = `<span class="tn-badge tn-badge-idle">IDLE</span>`;
        if (node.status === 'RUNNING') {
            statusBadge = `<span class="tn-badge tn-badge-running">● RUNNING</span>`;
        } else if (node.status === 'STARTING') {
            statusBadge = `<span class="tn-badge tn-badge-starting">⏳ STARTING</span>`;
        } else if (node.status === 'STOPPED') {
            statusBadge = `<span class="tn-badge tn-badge-stopped">■ STOPPED</span>`;
        } else if (node.status === 'ERROR') {
            statusBadge = `<span class="tn-badge tn-badge-error" title="${node.error || 'Error'}">✖ ERROR</span>`;
        }

        const endpointText = isSS
            ? (node.endpoint || 'WireGuard')
            : (node.host ? `${node.host}:${node.port}` : '-');

        const localPortText = isSS
            ? `127.0.0.1:${node.port} (SOCKS5)`
            : `${(node.protocol || 'HTTP').toUpperCase()}`;

        let healthText = '-';
        if (isSS) {
            healthText = `<span style="color: #38bdf8;">WireGuard 0.0ms</span>`;
        } else if (node.is_alive === true) {
            healthText = `<span style="color: #22c55e;">${node.latency_ms || 0} ms</span>`;
        } else if (node.is_alive === false) {
            healthText = `<span style="color: #f87171;" title="${node.error || 'Failed'}">Offline</span>`;
        }

        const trafficText = `${formatBytes(node.bytes_in || 0)} / ${formatBytes(node.bytes_out || 0)}`;
        const uptimeText = formatUptime(node.uptime_seconds);

        const isRunning = (node.status === 'RUNNING' || node.status === 'STARTING');
        const startBtn = isRunning
            ? `<button type="button" class="tn-btn-action" onclick="stopNode(${node.id})">Stop</button>`
            : `<button type="button" class="tn-btn-action" onclick="startNode(${node.id})">Start</button>`;
        const delBtn = `<button type="button" class="tn-btn-action" onclick="deleteNode(${node.id})" title="Hapus node #${node.id}" style="color: #ff5252; margin-left: 4px;">🗑️</button>`;

        html += `
            <tr>
                <td><strong>#${node.id}</strong></td>
                <td>${typeBadge}</td>
                <td>${statusBadge}</td>
                <td style="color: #f8fafc;">${node.device_name || `Node-${node.id}`}</td>
                <td style="color: #94a3b8;">${endpointText}</td>
                <td>${localPortText}</td>
                <td>${healthText}</td>
                <td>${trafficText}</td>
                <td>${uptimeText}</td>
                <td style="text-align: right; white-space: nowrap;">
                    ${startBtn}
                    <button type="button" class="tn-btn-action" onclick="viewNodeLog(${node.id})">Log</button>
                    ${delBtn}
                </td>
            </tr>
        `;
    }
    nodesTbody.innerHTML = html;
}

// FILTER PILLS EVENT LISTENERS & FUNCTION
window.setTableFilter = function(filterName, btnEl) {
    document.querySelectorAll('.tn-pill, .tn-pill-btn').forEach(b => b.classList.remove('active'));
    if (btnEl) {
        btnEl.classList.add('active');
    } else {
        const target = document.querySelector(`[data-filter="${filterName}"]`);
        if (target) target.classList.add('active');
    }
    activeFilter = filterName || 'all';
    if (currentStatusData && currentStatusData.nodes) {
        renderTable(currentStatusData.nodes);
    }
};

document.querySelectorAll('.tn-pill, .tn-pill-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        window.setTableFilter(btn.dataset.filter || 'all', btn);
    });
});

if (tableFilter) {
    tableFilter.addEventListener('input', () => {
        if (currentStatusData && currentStatusData.nodes) {
            renderTable(currentStatusData.nodes);
        }
    });
}

// SAVE CONFIG TOKEN
if (btnSaveToken) {
    btnSaveToken.addEventListener('click', async () => {
        const token = (cfgToken.value || '').trim();
        if (!token) {
            showToast("Token TraffMonetizer tidak boleh kosong!", true);
            return;
        }
        btnSaveToken.disabled = true;
        btnSaveToken.textContent = "Menyimpan...";
        try {
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    traff_token: token,
                    surfshark_private_key: (cfgSurfsharkKey.value || '').trim(),
                    surfshark_region: cfgSurfsharkRegion ? cfgSurfsharkRegion.value : 'all',
                    surfshark_node_count: cfgSurfsharkCount ? parseInt(cfgSurfsharkCount.value) : 50,
                    surfshark_start_port: cfgSurfsharkPort ? parseInt(cfgSurfsharkPort.value) : 21000
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast("Token & Konfigurasi berhasil disimpan!");
                fetchStatus();
            } else {
                showToast(data.message || "Gagal menyimpan konfigurasi", true);
            }
        } catch (e) {
            showToast("Gagal menghubungi server", true);
        } finally {
            btnSaveToken.disabled = false;
            btnSaveToken.textContent = "Simpan";
        }
    });
}

// GENERATE SURFSHARK NODES (NON-DESTRUCTIVE POOL)
if (btnGenerateSurfshark) {
    btnGenerateSurfshark.addEventListener('click', async () => {
        const privkey = (cfgSurfsharkKey.value || '').trim();
        const region = cfgSurfsharkRegion ? cfgSurfsharkRegion.value : 'all';
        const count = cfgSurfsharkCount ? parseInt(cfgSurfsharkCount.value) : 50;
        const startPort = cfgSurfsharkPort ? parseInt(cfgSurfsharkPort.value) : 21000;
        const mode = cfgSurfsharkMode ? cfgSurfsharkMode.value : 'replace';

        if (!privkey) {
            showToast("Harap isi WireGuard Private Key Surfshark terlebih dahulu!", true);
            return;
        }

        btnGenerateSurfshark.disabled = true;
        if (txtBtnGenSs) txtBtnGenSs.textContent = "🦈 Meng-generate Server Fisik...";
        try {
            const res = await fetch('/api/surfshark/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    private_key: privkey,
                    region: region,
                    node_count: count,
                    start_port: startPort,
                    mode: mode
                })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                showToast(data.message || `Berhasil men-generate ${count} node Surfshark!`);
                await fetchStatus();
            } else {
                showToast(data.detail || data.message || "Gagal generate node Surfshark", true);
            }
        } catch (e) {
            showToast("Koneksi gagal saat generate Surfshark", true);
        } finally {
            btnGenerateSurfshark.disabled = false;
            if (txtBtnGenSs) txtBtnGenSs.textContent = "🦈 GENERATE & SIMPAN SURFSHARK";
        }
    });
}

// CLEAR SURFSHARK POOL
if (btnClearSurfshark) {
    btnClearSurfshark.addEventListener('click', async () => {
        if (!confirm("Yakin ingin menghapus seluruh node Surfshark dari pool? Custom Proxy tidak akan terhapus.")) {
            return;
        }
        btnClearSurfshark.disabled = true;
        try {
            const res = await fetch('/api/nodes/surfshark', { method: 'DELETE' });
            const data = await res.json();
            showToast(data.message || "Pool Surfshark telah dibersihkan.");
            fetchStatus();
        } catch (e) {
            showToast("Gagal menghapus pool Surfshark", true);
        } finally {
            btnClearSurfshark.disabled = false;
        }
    });
}

// SAVE CUSTOM PROXIES (NON-DESTRUCTIVE POOL)
if (btnSaveProxies) {
    btnSaveProxies.addEventListener('click', async () => {
        const raw = (proxiesTextarea.value || '').trim();
        const mode = cfgProxiesMode ? cfgProxiesMode.value : 'replace';

        if (!raw) {
            showToast("Daftar proxy tidak boleh kosong!", true);
            return;
        }

        btnSaveProxies.disabled = true;
        if (txtBtnSavePx) txtBtnSavePx.textContent = "💾 Menyimpan...";
        try {
            const res = await fetch('/api/proxies', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ raw_text: raw, mode: mode })
            });
            const data = await res.json();
            if (data.success) {
                showToast(data.message || `Berhasil menyimpan ${data.count} proxy!`);
                await fetchStatus();
            } else {
                showToast(data.message || "Gagal menyimpan proxy", true);
            }
        } catch (e) {
            showToast("Koneksi gagal saat menyimpan proxy", true);
        } finally {
            btnSaveProxies.disabled = false;
            if (txtBtnSavePx) txtBtnSavePx.textContent = "💾 SIMPAN PROXY";
        }
    });
}

// TEST CUSTOM PROXIES HEALTH
if (btnCheckProxies) {
    btnCheckProxies.addEventListener('click', async () => {
        btnCheckProxies.disabled = true;
        if (txtBtnCheckPx) txtBtnCheckPx.textContent = "🩺 Memeriksa...";
        try {
            const res = await fetch('/api/check', { method: 'POST' });
            const data = await res.json();
            showToast(data.message || "Pengecekan koneksi proxy dimulai!");
            setTimeout(fetchStatus, 1500);
        } catch (e) {
            showToast("Gagal memulai pengecekan proxy", true);
        } finally {
            btnCheckProxies.disabled = false;
            if (txtBtnCheckPx) txtBtnCheckPx.textContent = "🩺 TEST KONEKSI PROXY";
        }
    });
}

// CLEAR PROXIES POOL
if (btnClearProxies) {
    btnClearProxies.addEventListener('click', async () => {
        if (!confirm("Yakin ingin menghapus seluruh Custom Proxy? Node Surfshark tidak akan terhapus.")) {
            return;
        }
        btnClearProxies.disabled = true;
        try {
            const res = await fetch('/api/nodes/proxies', { method: 'DELETE' });
            const data = await res.json();
            if (proxiesTextarea) proxiesTextarea.value = "";
            updateProxyLineCount();
            showToast(data.message || "Pool Custom Proxy telah dibersihkan.");
            fetchStatus();
        } catch (e) {
            showToast("Gagal menghapus custom proxy", true);
        } finally {
            btnClearProxies.disabled = false;
        }
    });
}

// MASTER CONTROLS: START ALL
if (btnStartAll) {
    btnStartAll.addEventListener('click', async () => {
        btnStartAll.disabled = true;
        if (txtBtnStartAll) txtBtnStartAll.textContent = "🚀 Menjalankan...";
        try {
            const res = await fetch('/api/start-all', { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.success) {
                showToast(data.message || `Berhasil memulai ${data.started} node!`);
                await fetchStatus();
            } else {
                showToast(data.detail || data.message || "Gagal menjalankan all workers", true);
            }
        } catch (e) {
            showToast("Koneksi gagal saat start all", true);
        } finally {
            btnStartAll.disabled = false;
            if (txtBtnStartAll) txtBtnStartAll.textContent = "🚀 START ALL WORKERS";
            renderDashboard(currentStatusData || {});
        }
    });
}

// MASTER CONTROLS: STOP ALL
if (btnStopAll) {
    btnStopAll.addEventListener('click', async () => {
        btnStopAll.disabled = true;
        if (txtBtnStopAll) txtBtnStopAll.textContent = "🛑 Menghentikan...";
        try {
            const res = await fetch('/api/stop-all', { method: 'POST' });
            const data = await res.json();
            showToast(data.message || "Seluruh worker node telah dihentikan.");
            await fetchStatus();
        } catch (e) {
            showToast("Gagal menghentikan workers", true);
        } finally {
            btnStopAll.disabled = false;
            if (txtBtnStopAll) txtBtnStopAll.textContent = "🛑 STOP ALL";
        }
    });
}

// SELECTIVE START SURFSHARK ONLY
if (btnStartSs) {
    btnStartSs.addEventListener('click', async () => {
        btnStartSs.disabled = true;
        if (txtBtnStartSs) txtBtnStartSs.textContent = "▶ Memulai...";
        try {
            const res = await fetch('/api/start-surfshark', { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.success) {
                showToast(data.message || `Berhasil start ${data.started} node Surfshark!`);
                await fetchStatus();
            } else {
                showToast(data.detail || data.message || "Gagal start Surfshark", true);
            }
        } catch (e) {
            showToast("Koneksi gagal saat start Surfshark", true);
        } finally {
            btnStartSs.disabled = false;
            if (txtBtnStartSs) txtBtnStartSs.textContent = "▶ Start Surfshark";
        }
    });
}

// SELECTIVE START CUSTOM PROXY ONLY
if (btnStartPx) {
    btnStartPx.addEventListener('click', async () => {
        btnStartPx.disabled = true;
        if (txtBtnStartPx) txtBtnStartPx.textContent = "▶ Memulai...";
        try {
            const res = await fetch('/api/start-proxies', { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.success) {
                showToast(data.message || `Berhasil start ${data.started} proxy!`);
                await fetchStatus();
            } else {
                showToast(data.detail || data.message || "Gagal start proxies", true);
            }
        } catch (e) {
            showToast("Koneksi gagal saat start proxies", true);
        } finally {
            btnStartPx.disabled = false;
            if (txtBtnStartPx) txtBtnStartPx.textContent = "▶ Start Proxy";
        }
    });
}

// RESTART ALL
if (btnRestartAll) {
    btnRestartAll.addEventListener('click', async () => {
        btnRestartAll.disabled = true;
        if (txtBtnRestartAll) txtBtnRestartAll.textContent = "🔄 Me-restart...";
        try {
            const res = await fetch('/api/restart-all', { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.success) {
                showToast(data.message || "Seluruh node di-restart!");
                await fetchStatus();
            } else {
                showToast(data.detail || data.message || "Gagal restart", true);
            }
        } catch (e) {
            showToast("Koneksi gagal saat restart", true);
        } finally {
            btnRestartAll.disabled = false;
            if (txtBtnRestartAll) txtBtnRestartAll.textContent = "🔄 Restart All";
        }
    });
}

// STOP SURFSHARK ONLY
if (btnStopSs) {
    btnStopSs.addEventListener('click', async () => {
        btnStopSs.disabled = true;
        if (txtBtnStopSs) txtBtnStopSs.textContent = "🛑 Menghentikan...";
        try {
            const res = await fetch('/api/stop-surfshark', { method: 'POST' });
            const data = await res.json();
            showToast(data.message || "Surfshark dihentikan.");
            await fetchStatus();
        } catch (e) {
            showToast("Gagal stop Surfshark", true);
        } finally {
            btnStopSs.disabled = false;
            if (txtBtnStopSs) txtBtnStopSs.textContent = "🛑 Stop SS";
        }
    });
}

// STOP PROXY ONLY
if (btnStopPx) {
    btnStopPx.addEventListener('click', async () => {
        btnStopPx.disabled = true;
        if (txtBtnStopPx) txtBtnStopPx.textContent = "🛑 Menghentikan...";
        try {
            const res = await fetch('/api/stop-proxies', { method: 'POST' });
            const data = await res.json();
            showToast(data.message || "Custom Proxy dihentikan.");
            await fetchStatus();
        } catch (e) {
            showToast("Gagal stop Custom Proxy", true);
        } finally {
            btnStopPx.disabled = false;
            if (txtBtnStopPx) txtBtnStopPx.textContent = "🛑 Stop PX";
        }
    });
}

// SINGLE NODE START
window.startNode = async function(nodeId) {
    try {
        const res = await fetch(`/api/node/${nodeId}/start`, { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast(`Node #${nodeId} berhasil dijalankan.`);
            fetchStatus();
        } else {
            showToast(data.detail || "Gagal start node", true);
        }
    } catch (e) {
        showToast("Koneksi gagal saat start node", true);
    }
};

// SINGLE NODE STOP
window.stopNode = async function(nodeId) {
    try {
        const res = await fetch(`/api/node/${nodeId}/stop`, { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast(`Node #${nodeId} dihentikan.`);
            fetchStatus();
        } else {
            showToast(data.detail || "Gagal stop node", true);
        }
    } catch (e) {
        showToast("Koneksi gagal saat stop node", true);
    }
};

// PURGE ERROR NODES
const btnPurgeError = document.getElementById('btn-purge-error');
if (btnPurgeError) {
    btnPurgeError.addEventListener('click', async () => {
        if (!confirm("Hapus semua node yang berstatus ERROR atau offline?")) return;
        btnPurgeError.disabled = true;
        try {
            const res = await fetch('/api/nodes/error', { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                showToast(data.message);
                fetchStatus();
            } else {
                showToast(data.message || "Gagal membersihkan error", true);
            }
        } catch (e) {
            showToast("Gagal menghubungi server", true);
        } finally {
            btnPurgeError.disabled = false;
        }
    });
}

// EXPORT LIVE PROXIES
const btnExportProxies = document.getElementById('btn-export-proxies');
if (btnExportProxies) {
    btnExportProxies.addEventListener('click', () => {
        window.open('/api/export/live-proxies', '_blank');
    });
}

// EXPORT LIVE CONFIG
const btnExportConfig = document.getElementById('btn-export-config');
if (btnExportConfig) {
    btnExportConfig.addEventListener('click', () => {
        window.open('/api/export/live-config', '_blank');
    });
}

// DELETE SINGLE NODE
window.deleteNode = async function(nodeId) {
    if (!confirm(`Hapus node #${nodeId}?`)) return;
    try {
        const res = await fetch(`/api/node/${nodeId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast(data.message);
            fetchStatus();
        } else {
            showToast(data.message || "Gagal menghapus node", true);
        }
    } catch (e) {
        showToast("Gagal menghubungi server", true);
    }
};

// LOG MODAL OPERATIONS
window.viewNodeLog = async function(nodeId) {
    currentLogNodeId = nodeId;
    if (logModalTitle) logModalTitle.textContent = `Worker Log: Node #${nodeId}`;
    if (logModalBody) logModalBody.textContent = "Mengambil log worker...";
    if (logModal) logModal.style.display = 'block';

    try {
        const res = await fetch(`/api/node/${nodeId}/logs`);
        const text = await res.text();
        if (logModalBody) logModalBody.textContent = text || "Belum ada log tercatat.";
    } catch (e) {
        if (logModalBody) logModalBody.textContent = "Gagal mengambil log dari server.";
    }
};

if (btnCloseModal) {
    btnCloseModal.addEventListener('click', () => {
        if (logModal) logModal.style.display = 'none';
        currentLogNodeId = null;
    });
}

if (btnRefreshLog) {
    btnRefreshLog.addEventListener('click', () => {
        if (currentLogNodeId !== null) {
            window.viewNodeLog(currentLogNodeId);
        }
    });
}

// KEYBOARD ACCESSIBILITY: ESCAPE TO CLOSE MODAL (R-32)
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && logModal && logModal.style.display === 'block') {
        logModal.style.display = 'none';
        currentLogNodeId = null;
    }
});

// CLOSE MODAL ON OUTSIDE CLICK
window.addEventListener('click', (e) => {
    if (e.target === logModal) {
        logModal.style.display = 'none';
        currentLogNodeId = null;
    }
});

// INITIAL BOOTSTRAP
document.addEventListener('DOMContentLoaded', () => {
    fetchStatus();
    fetchRawProxies();
    pollTimer = setInterval(fetchStatus, 4000);
});
