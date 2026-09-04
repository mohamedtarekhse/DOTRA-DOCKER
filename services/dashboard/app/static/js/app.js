// ACUSEEK dashboard interactions
// WebSocket connection for live alerts & gate events + global Fiori search

const WS_URL = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws/events';

let wsRetry = 1;
let wsTimer = null;

function showToast(message, type) {
    const t = document.createElement('div');
    t.className = 'toast' + (type ? ' ' + type : '');
    t.textContent = message || 'Event received';
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 5000);
}

function bumpAlertBadge() {
    const badge = document.getElementById('alert-badge');
    if (!badge) return;
    const cur = parseInt(badge.textContent.replace(/\D/g, '')) || 0;
    const n = cur + 1;
    badge.textContent = n;
}

function addLiveEvent(icon, title, sub, color) {
    const list = document.getElementById('live-events');
    if (!list) return;
    const li = document.createElement('li');
    li.className = 'ev';
    li.innerHTML = '<span class="dot ' + (color || 'dot-ok') + '"></span>'
        + '<div><div class="t">' + (title || 'Event') + '</div>'
        + '<div class="s">' + (sub || '') + '</div></div>';
    list.prepend(li);
    // keep max 20 events
    while (list.children.length > 20) list.removeChild(list.lastChild);
}

function handleWSMessage(raw) {
    let data;
    try { data = JSON.parse(raw); } catch (e) { return; }
    if (!data || typeof data !== 'object') return;

    if (data.type === 'alert') {
        bumpAlertBadge();
        showToast('ALERT: ' + (data.description || (data.alert_type + ' in ' + (data.zone || '?'))));
        addLiveEvent('🚨',
            '<span class="badge badge-error">' + data.alert_type + '</span> ' + (data.zone || ''),
            data.description,
            'dot-err');
    } else if (data.type === 'gate_event') {
        const decision = data.decision || {};
        const action = decision.action || data.event_type || 'event';
        const allowed = decision.allowed;
        const color = allowed ? 'dot-ok' : 'dot-err';
        showToast(data.plate + ' ' + data.direction + ' → ' + action,
            allowed ? 'info' : '');
        addLiveEvent(
            allowed ? '✅' : '🚫',
            '<span class="mono">' + (data.plate || '?') + '</span> ' + data.direction,
            action + (data.approved !== undefined ? ' (by ' + (data.manager || '') + ')' : ''),
            color);
    }
}

function connectWS() {
    let ws;
    try { ws = new WebSocket(WS_URL); } catch (e) { return; }
    ws.onopen = () => {
        wsRetry = 1;
        console.log('Connected to live events');
        const b = document.getElementById('livestream-badge');
        if (b) { b.textContent = 'connected'; b.className = 'badge badge-ok'; }
    };
    ws.onmessage = (e) => handleWSMessage(e.data);
    ws.onclose = () => {
        const b = document.getElementById('livestream-badge');
        if (b) { b.textContent = 'reconnecting…'; b.className = 'badge badge-warn'; }
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
        dot.textContent = '●';
        dot.style.color = resp.ok ? '#188918' : '#bb0000';
    } catch (e) {
        dot.textContent = '○';
        dot.style.color = '#bb0000';
    }
}

// ---- Fiori Global Search ----
const NAV_ITEMS = [
    { label: 'Dashboard',   href: '/',            keys: ['dashboard','home','overview'] },
    { label: 'Gates',       href: '/gates',        keys: ['gates','barrier','entry','exit'] },
    { label: 'Vehicles',    href: '/vehicles',     keys: ['vehicles','whitelist','plates'] },
    { label: 'Pre-Approvals', href: '/preapprovals', keys: ['preapprovals','permits','xlsx'] },
    { label: 'Persons',     href: '/persons',      keys: ['persons','people','face','enroll'] },
    { label: 'Alerts',      href: '/alerts',       keys: ['alerts','security','intrusion'] },
    { label: 'Image Search', href: '/search',      keys: ['search','images','snapshots'] },
    { label: 'Settings',    href: '/settings',     keys: ['settings','config','cameras','zones'] },
];

function setupGlobalSearch() {
    const input = document.getElementById('global-search');
    const dd = document.getElementById('search-dd');
    if (!input || !dd) return;

    function renderDropdown(q) {
        if (!q || q.length < 1) { dd.classList.remove('open'); dd.innerHTML = ''; return; }
        const lower = q.toLowerCase();
        let html = '<div class="sd-head">Navigate</div>';
        let any = false;
        for (const item of NAV_ITEMS) {
            if (item.label.toLowerCase().includes(lower) ||
                item.keys.some(k => k.includes(lower))) {
                html += '<a class="sd-item" href="' + item.href + '">' + item.label + '</a>';
                any = true;
            }
        }
        html += '<div class="sd-head">Image Search</div>';
        html += '<a class="sd-item" href="/search?q=' + encodeURIComponent(q) + '">Search for "' + q.replace(/"/g, '&quot;') + '"…</a>';
        dd.innerHTML = html;
        dd.classList.add('open');
    }

    input.addEventListener('input', () => renderDropdown(input.value));
    input.addEventListener('focus', () => renderDropdown(input.value));

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const q = input.value.trim();
            if (q) location.href = '/search?q=' + encodeURIComponent(q);
            dd.classList.remove('open');
        } else if (e.key === 'Escape') {
            dd.classList.remove('open');
        }
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('#shell-search')) dd.classList.remove('open');
    });
}

window.addEventListener('DOMContentLoaded', () => {
    connectWS();
    pollHealth();
    setInterval(pollHealth, 30000);
    setupGlobalSearch();
});
