// ── Wave Background Animation ──────────────────────────
(function() {
  const canvas = document.getElementById('wave-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let animationId;
  let time = 0;
  const mouse = { x: -1000, y: -1000 };

  const resize = () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  };
  resize();
  window.addEventListener('resize', resize);

  window.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
  });

  const draw = () => {
    const { width, height } = canvas;
    const lineCount = 60;

    ctx.fillStyle = '#0024ff';
    ctx.fillRect(0, 0, width, height);

    for (let i = 0; i < lineCount; i++) {
      const baseY = (i / lineCount) * height;
      const opacity = 0.06 + (i / lineCount) * 0.14;

      ctx.beginPath();
      ctx.strokeStyle = `rgba(255, 255, 255, ${opacity})`;
      ctx.lineWidth = 1.5;

      for (let x = 0; x <= width; x += 4) {
        const distFromCenter = Math.abs(x - width * 0.35);
        const centerInfluence = Math.max(0, 1 - distFromCenter / (width * 0.5));

        const wave1 = Math.sin(x * 0.008 + time * 0.001 + i * 0.15) * 25;
        const wave2 = Math.sin(x * 0.02 - time * 0.0015 + i * 0.08) * 12;
        const wave3 = Math.sin(x * 0.003 + time * 0.0008) * 18 * centerInfluence;

        let mouseDent = 0;
        const dx = x - mouse.x;
        const dy = baseY - mouse.y;
        const distToMouse = Math.sqrt(dx * dx + dy * dy);
        const dentRadius = 160;

        if (distToMouse < dentRadius) {
          const angle = Math.atan2(dy, dx);
          const irregularity = Math.sin(angle * 3 + time * 0.002) * 20 +
                               Math.sin(angle * 7 - time * 0.001) * 12 +
                               Math.cos(angle * 5 + time * 0.0015) * 15;
          const effectiveRadius = dentRadius + irregularity;
          if (distToMouse < effectiveRadius) {
            const strength = Math.pow(1 - distToMouse / effectiveRadius, 2) * 60;
            mouseDent = strength * Math.sin(x * 0.05 + time * 0.003);
          }
        }

        const y = baseY + wave1 + wave2 + wave3 + mouseDent;

        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    time += 16;
    animationId = requestAnimationFrame(draw);
  };

  draw();
})();

// ── Lucide Icons (SVG) ─────────────────────────────────
const Icons = {
  Play: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
  Square: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>',
  Wallet: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/></svg>',
  RefreshCw: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>',
  TrendingUp: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
  TrendingDown: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>',
  Bot: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>',
  CheckCircle: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
  XCircle: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
  X: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
};

// ── Drawer Functions ───────────────────────────────────
function toggleDrawer() {
  const overlay = document.getElementById('drawer-overlay');
  const drawer = document.getElementById('wallet-drawer');
  overlay.classList.toggle('open');
  drawer.classList.toggle('open');
}

function closeDrawer() {
  const overlay = document.getElementById('drawer-overlay');
  const drawer = document.getElementById('wallet-drawer');
  overlay.classList.remove('open');
  drawer.classList.remove('open');
}

// ── Engine Toggle ──────────────────────────────────────
let engineRunning = false;

function toggleEngine() {
  engineRunning = !engineRunning;
  const btn = document.getElementById('engine-btn');
  if (engineRunning) {
    btn.innerHTML = `${Icons.Square} STOP`;
    btn.classList.remove('start');
    btn.classList.add('stop');
    runTest();
  } else {
    btn.innerHTML = `${Icons.Play} START`;
    btn.classList.remove('stop');
    btn.classList.add('start');
  }
}

// ── Paper Toggle ───────────────────────────────────────
let paperTrading = true;

function togglePaper() {
  paperTrading = !paperTrading;
  const track = document.getElementById('toggle-track');
  const label = document.getElementById('toggle-label');
  track.classList.toggle('active', paperTrading);
  label.textContent = paperTrading ? 'PAPER' : 'LIVE';
}

// ── API Functions ──────────────────────────────────────
async function fetchJSON(url) {
  const response = await fetch(url);
  return response.json();
}

function formatNumber(num, decimals = 2) {
  if (num === undefined || num === null) return '--';
  return Number(num).toLocaleString(undefined, {minimumFractionDigits: decimals, maximumFractionDigits: decimals});
}

// ── Exchange Balances Drawer ───────────────────────────
async function fetchBalances() {
  const container = document.getElementById('drawer-balances');
  container.innerHTML = '<span class="drawer-system-text">Loading...</span>';

  try {
    const data = await fetchJSON('/api/balances');

    if (!data.exchanges || data.exchanges.length === 0) {
      container.innerHTML = '<span class="balance-value error">No exchanges configured</span>';
      return;
    }

    let html = '';
    for (const ex of data.exchanges) {
      html += `<div class="exchange-section">`;
      html += `<div class="exchange-name">`;
      if (ex.error) {
        html += `<span class="status-dot error"></span>${ex.exchange || 'unknown'} — ${ex.error}`;
      } else {
        html += `<span class="status-dot"></span>${ex.exchange}`;
        if (ex.equity) {
          html += `<span style="margin-left:auto; color: var(--accent);">$${formatNumber(ex.equity)}</span>`;
        } else if (ex.total_usdt_approx) {
          html += `<span style="margin-left:auto; color: var(--accent);">$${formatNumber(ex.total_usdt_approx)}</span>`;
        }
      }
      html += `</div>`;

      if (!ex.error) {
        if (ex.balances) {
          for (const [asset, bal] of Object.entries(ex.balances).slice(0, 10)) {
            html += `<div class="balance-item">
              <span class="balance-label">${asset}</span>
              <span class="balance-value">${formatNumber(bal.total, 4)}</span>
            </div>`;
          }
          if (Object.keys(ex.balances).length > 10) {
            html += `<div class="balance-item"><span class="balance-label">...and ${Object.keys(ex.balances).length - 10} more</span></div>`;
          }
        } else if (ex.cash !== undefined) {
          html += `<div class="balance-item"><span class="balance-label">Cash</span><span class="balance-value">$${formatNumber(ex.cash)}</span></div>`;
          html += `<div class="balance-item"><span class="balance-label">Buying Power</span><span class="balance-value">$${formatNumber(ex.buying_power)}</span></div>`;
        }
      }
      html += `</div>`;
    }

    html += `<div class="total-equity">
      <span class="total-label">TOTAL EQUITY</span>
      <span class="total-value">$${formatNumber(data.total_equity_usd)}</span>
    </div>`;

    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<span class="balance-value error">Error: ${e.message}</span>`;
  }
}

// ── Status ─────────────────────────────────────────────
async function refreshStatus() {
  try {
    const data = await fetchJSON('/api/status');
    document.getElementById('stat-trades').textContent = data.total_trades || 0;
    document.getElementById('stat-winrate').textContent = data.win_rate || '0%';
    document.getElementById('stat-pnl').textContent = (data.total_pnl || '0.00') + '%';
    document.getElementById('stat-pnl').className = 'stat-value ' + (parseFloat(data.total_pnl) >= 0 ? 'positive' : 'negative');
    document.getElementById('stat-capital').textContent = '$' + (data.capital || '0.00').replace(/,/g, '');
    document.getElementById('stat-positions').textContent = data.open_positions || 0;
    document.getElementById('stat-pairs').textContent = data.watchlist_size || 0;
  } catch (e) {
    console.error('Failed to refresh status:', e);
  }
}

// ── Actions Feed ───────────────────────────────────────
function addAction(icon, type, title, detail, profit) {
  const feed = document.getElementById('actions-feed');
  const emptyMsg = feed.querySelector('.empty-message');
  if (emptyMsg) emptyMsg.remove();

  const item = document.createElement('div');
  item.className = 'action-item';

  let iconSvg = '';
  if (type === 'buy') iconSvg = Icons.TrendingUp;
  else if (type === 'sell') iconSvg = Icons.TrendingDown;
  else if (type === 'ai') iconSvg = Icons.Bot;
  else if (type === 'win') iconSvg = Icons.CheckCircle;
  else if (type === 'loss') iconSvg = Icons.XCircle;

  item.innerHTML = `
    <div class="action-icon ${type}">${iconSvg}</div>
    <div class="action-content">
      <div class="action-title">${title}</div>
      <div class="action-detail">${detail}</div>
    </div>
    ${profit !== null ? `<div class="action-profit ${profit >= 0 ? 'positive' : 'negative'}">${profit >= 0 ? '+' : ''}${formatNumber(profit)}%</div>` : ''}
  `;
  feed.insertBefore(item, feed.firstChild);

  while (feed.children.length > 50) {
    feed.removeChild(feed.lastChild);
  }
}

// ── AI Predictions Display ─────────────────────────────
function displayAIPredictions(predictions) {
  const container = document.getElementById('ai-predictions');
  if (!predictions || predictions.length === 0) {
    container.innerHTML = '<span style="color: rgba(255,255,255,0.5); font-size: 0.8rem;">No active predictions</span>';
    return;
  }

  let html = '';
  for (const pred of predictions) {
    const signalColor = pred.direction === 'long' ? 'var(--accent)' : 'var(--danger)';
    html += `<div class="ai-prediction">
      <div class="ai-icon">${Icons.Bot}</div>
      <div class="ai-info">
        <div class="ai-signal" style="color: ${signalColor}">${pred.symbol} — ${pred.direction.toUpperCase()}</div>
        <div class="ai-reason">${pred.reason}</div>
      </div>
      <div class="ai-confidence">${pred.confidence}%</div>
    </div>`;
  }
  container.innerHTML = html;
}

// ── Test Runner ────────────────────────────────────────
async function runTest() {
  const actionsEl = document.getElementById('actions-feed');
  actionsEl.innerHTML = '<div class="empty-message" style="color: rgba(255,255,255,0.5); text-align: center; padding: 20px;">Running analysis...</div>';

  try {
    const data = await fetchJSON('/api/test');

    if (data.ai_predictions) {
      displayAIPredictions(data.ai_predictions);
    }

    if (data.actions && data.actions.length > 0) {
      actionsEl.innerHTML = '';
      for (const action of data.actions) {
        addAction(action.icon, action.type, action.title, action.detail, action.profit);
      }
    }

    refreshStatus();
    fetchBalances();
  } catch (e) {
    actionsEl.innerHTML = `<div class="empty-message" style="color: var(--danger); text-align: center; padding: 20px;">Error: ${e.message}</div>`;
  }
}

// ── Init ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  fetchBalances();
  refreshStatus();
});

// Auto-refresh every 30 seconds
setInterval(refreshStatus, 30000);
setInterval(fetchBalances, 60000);
