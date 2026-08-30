// amphetamin_Overdose Dashboard JavaScript

async function fetchJSON(url) {
    const response = await fetch(url);
    return response.json();
}

async function postJSON(url) {
    const response = await fetch(url, { method: 'POST' });
    return response.json();
}

function formatNumber(num, decimals = 2) {
    if (num === undefined || num === null) return '--';
    return Number(num).toFixed(decimals);
}

function formatCurrency(num) {
    if (num === undefined || num === null) return '--';
    return '$' + Number(num).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

async function refreshStatus() {
    try {
        const status = await fetchJSON('/api/status');

        document.getElementById('stat-trades').textContent = status.total_trades || 0;
        document.getElementById('stat-winrate').textContent = status.win_rate ? (status.win_rate * 100).toFixed(1) + '%' : '--';
        document.getElementById('stat-pnl').textContent = status.total_pnl_pct ? status.total_pnl_pct.toFixed(2) + '%' : '--';
        document.getElementById('stat-pnl').className = 'stat-value ' + (status.total_pnl_pct >= 0 ? 'positive' : 'negative');
        document.getElementById('stat-positions').textContent = status.open_positions || 0;
        document.getElementById('stat-pairs').textContent = status.watchlist_size || 0;

        if (status.daily_stats) {
            document.getElementById('stat-loss-streak').textContent = status.daily_stats.loss_streak || 0;
        }

        // Update engine status badge
        const badge = document.getElementById('engine-status');
        if (status.is_running) {
            badge.textContent = 'RUNNING';
            badge.className = 'badge badge-success';
        } else {
            badge.textContent = 'STOPPED';
            badge.className = 'badge badge-danger';
        }

        // Load trades and pairs
        loadTrades();
        loadPairs();

    } catch (e) {
        console.error('Failed to refresh status:', e);
    }
}

async function loadTrades() {
    try {
        const data = await fetchJSON('/api/trades');
        const tbody = document.getElementById('trades-body');

        if (data.error) {
            tbody.innerHTML = `<tr><td colspan="7">${data.error}</td></tr>`;
            return;
        }

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="loading">No trades yet</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(t => `
            <tr>
                <td><strong>${t.symbol}</strong></td>
                <td class="${t.direction === 'long' ? 'positive' : 'negative'}">${t.direction.toUpperCase()}</td>
                <td>${t.status}</td>
                <td>${formatNumber(t.entry_price, 4)}</td>
                <td>${t.exit_price ? formatNumber(t.exit_price, 4) : '--'}</td>
                <td class="${t.pnl_pct >= 0 ? 'positive' : 'negative'}">${formatNumber(t.pnl_pct)}%</td>
                <td>${t.strategy || '--'}</td>
            </tr>
        `).join('');

    } catch (e) {
        console.error('Failed to load trades:', e);
    }
}

async function loadPairs() {
    try {
        const data = await fetchJSON('/api/pairs');
        const tbody = document.getElementById('pairs-body');

        if (data.error) {
            tbody.innerHTML = `<tr><td colspan="4">${data.error}</td></tr>`;
            return;
        }

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading">No pairs yet</td></tr>';
            return;
        }

        tbody.innerHTML = data.slice(0, 20).map(p => `
            <tr>
                <td><strong>${p.symbol}</strong></td>
                <td>${formatNumber(p.score, 1)}</td>
                <td>${formatCurrency(p.volume_24h)}</td>
                <td>${p.win_rate ? (p.win_rate * 100).toFixed(0) + '%' : '--'}</td>
            </tr>
        `).join('');

    } catch (e) {
        console.error('Failed to load pairs:', e);
    }
}

async function startEngine() {
    try {
        const result = await postJSON('/api/start');
        if (result.success) {
            alert('Trading engine started!');
            refreshStatus();
        } else {
            alert('Failed: ' + (result.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error starting engine: ' + e);
    }
}

async function stopEngine() {
    if (!confirm('Are you sure you want to stop the trading engine?')) return;
    try {
        const result = await postJSON('/api/stop');
        if (result.success) {
            alert('Trading engine stopped!');
            refreshStatus();
        }
    } catch (e) {
        alert('Error stopping engine: ' + e);
    }
}

async function scanMarket() {
    try {
        const result = await postJSON('/api/scan');
        if (result.success) {
            alert(`Scan complete! Found ${result.pairs_found} pairs.`);
            refreshStatus();
        } else {
            alert('Scan failed: ' + (result.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error scanning: ' + e);
    }
}

// Auto-refresh every 30 seconds
refreshStatus();
setInterval(refreshStatus, 30000);
