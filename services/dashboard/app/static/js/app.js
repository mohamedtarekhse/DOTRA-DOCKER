// ACUSEEK dashboard interactions
// WebSocket connection for live alerts & gate events

const WS_URL = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws/events';

let wsRetry = 1;
let wsTimer = null;

function showToast(message, color) {
    const t = document.createElement('div');
    t.className = 'fixed bottom-4 right-4 ' + (color || 'bg-red-600') +
        ' text-white px-4 py-3 rounded-lg shadow-lg z-50 max-w-md break-words';
    t.textContent = message || 'Event received';
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 5000);
}

function bumpAlertBadge() {
    const badge = document.getElementById('alert-badge');
    if (!badge) return;
    const m = badge.textContent.match(/\d+/);
    const n = m ? parseInt(m[0], 10) + 1 : 1;
    badge.textContent = n + ' alert' + (n === 1 ? '' : 's');
}

function handleWSMessage(raw) {
    let data;
    try {
        data = JSON.parse(raw);
    } catch (e) {
        console.warn('Non-JSON websocket frame ignored:', raw);
        return;
    }
    if (!data || typeof data !== 'object') return;

    if (data.type === 'alert') {
        bumpAlertBadge();
        showToast('🚨 ' + (data.description || (data.alert_type + ' in ' + (data.zone || '?'))));
    } else if (data.type === 'gate_event') {
        const decision = data.decision || {};
        const action = decision.action || data.event_type || 'event';
        showToast('🚧 ' + (data.plate || '?') + ' ' + data.direction + ' → ' + action, 'bg-blue-600');
    }
}

function connectWS() {
    let ws;
    try {
        ws = new WebSocket(WS_URL);
    } catch (e) {
        return;
    }
    ws.onopen = () => {
        wsRetry = 1;
        console.log('Connected to live events');
    };
    ws.onmessage = (e) => handleWSMessage(e.data);
    ws.onclose = () => {
        // Exponential backoff capped at 30s; pause when the tab is hidden.
        if (document.hidden) return;
        const delay = Math.min(1000 * Math.pow(2, Math.min(wsRetry, 5)), 30000);
        wsRetry += 1;
        wsTimer = setTimeout(connectWS, delay);
    };
    ws.onerror = () => { try { ws.close(); } catch (e) {} };
}

async function pollHealth() {
    const dot = document.getElementById('sys-status');
    if (!dot) return;
    try {
        const resp = await fetch('/api/health');
        dot.textContent = resp.ok ? '●' : '○';
        dot.classList.toggle('text-red-600', !resp.ok);
    } catch (e) {
        dot.textContent = '○';
        dot.classList.add('text-red-600');
    }
}

window.addEventListener('DOMContentLoaded', () => {
    connectWS();
    pollHealth();
    setInterval(pollHealth, 30000);
});