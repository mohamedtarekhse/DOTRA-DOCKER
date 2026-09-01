// ACUSEEK dashboard interactions
// WebSocket connection for live alerts

const WS_URL = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws/events';

function connectWS() {
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => console.log('Connected to live events');
    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'alert') {
            const badge = document.getElementById('alert-badge');
            if (badge) {
                const n = parseInt(badge.textContent) + 1;
                badge.textContent = n + ' alerts';
            }
            showToast(data.message);
        }
    };
    ws.onclose = () => setTimeout(connectWS, 3000);
    ws.onerror = () => ws.close();
}

function showToast(message) {
    const t = document.createElement('div');
    t.className = 'fixed bottom-4 right-4 bg-red-600 text-white px-4 py-3 rounded-lg shadow-lg z-50';
    t.textContent = message;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 5000);
}

window.addEventListener('DOMContentLoaded', connectWS);
