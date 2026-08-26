"""Live dashboard for visualizing the latest FlexSim telemetry.

Self-contained HTML/JS page (no external assets, no build step) that polls
GET /api/v1/state on an interval and renders queue levels as a bar chart
plus simple tables for processors and robots.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>FlexSim Digital Twin Bridge — Dashboard</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #0f1117;
    --panel: #171a23;
    --border: #2a2e3a;
    --text: #e6e8ef;
    --muted: #9aa1b2;
    --accent: #5b8cff;
    --ok: #37c26f;
    --bad: #ff6b6b;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
  }
  h1 { font-size: 18px; font-weight: 600; margin: 0 0 4px; }
  .sub { color: var(--muted); font-size: 13px; margin-bottom: 20px; }
  .grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 16px;
  }
  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
  }
  .panel h2 {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
    margin: 0 0 12px;
  }
  .stat-row { display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
  .stat {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
    min-width: 160px;
  }
  .stat .label { color: var(--muted); font-size: 12px; }
  .stat .value { font-size: 22px; font-weight: 600; margin-top: 4px; }
  .status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    background: var(--muted);
  }
  .status-dot.live { background: var(--ok); }
  .status-dot.stale { background: var(--bad); }
  canvas { width: 100%; height: 260px; display: block; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 500; }
  .empty { color: var(--muted); font-size: 13px; padding: 8px 0; }
  .topbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
  button#resetBtn {
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    cursor: pointer;
  }
  button#resetBtn:hover { border-color: var(--accent); }
  button#resetBtn:active { opacity: 0.7; }
</style>
</head>
<body>
  <div class="topbar">
    <div>
      <h1>FlexSim Digital Twin Bridge</h1>
      <div class="sub"><span id="statusDot" class="status-dot"></span><span id="statusText">connecting...</span></div>
    </div>
    <button id="resetBtn" title="Clear stored telemetry so you can see fresh data arrive on the next run">Reset</button>
  </div>

  <div class="stat-row">
    <div class="stat">
      <div class="label">Simulation Time</div>
      <div class="value" id="simTime">—</div>
    </div>
    <div class="stat">
      <div class="label">Model Status</div>
      <div class="value" id="modelStatus">—</div>
    </div>
    <div class="stat">
      <div class="label">Last Received</div>
      <div class="value" id="receivedAt" style="font-size:14px;">—</div>
    </div>
    <div class="stat" style="border-color: var(--ok);">
      <div class="label">Baskets In</div>
      <div class="value" id="basketsIn" style="color: var(--ok);">—</div>
    </div>
    <div class="stat" style="border-color: var(--accent);">
      <div class="label">Baskets Out</div>
      <div class="value" id="basketsOut" style="color: var(--accent);">—</div>
    </div>
  </div>

  <div class="grid">
    <div class="panel">
      <h2>Queue Levels</h2>
      <canvas id="queueChart"></canvas>
    </div>
    <div class="panel">
      <h2>Processors</h2>
      <table id="processorTable"><thead><tr><th>Name</th><th>State</th><th>Util.</th></tr></thead><tbody></tbody></table>
      <div id="processorEmpty" class="empty" style="display:none;">No processor data yet.</div>
    </div>
  </div>

  <div class="panel" style="margin-top:16px;">
    <h2>Robots / AGVs</h2>
    <table id="robotTable"><thead><tr><th>Name</th><th>X</th><th>Y</th><th>Speed</th><th>State</th><th>Battery</th></tr></thead><tbody></tbody></table>
    <div id="robotEmpty" class="empty" style="display:none;">No robot data yet.</div>
  </div>

<script>
const POLL_MS = 1000;
const canvas = document.getElementById('queueChart');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * devicePixelRatio;
  canvas.height = rect.height * devicePixelRatio;
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

// Tracks the highest value seen per queue since the last Reset, so a
// brief spike (item arrives then immediately leaves) stays visible
// instead of the bar collapsing back to 0 before anyone can see it.
let peakQueues = {};

function drawBarChart(queues) {
  const rect = canvas.getBoundingClientRect();
  const w = rect.width, h = rect.height;
  ctx.clearRect(0, 0, w, h);

  const names = Object.keys(queues);
  if (names.length === 0) {
    ctx.fillStyle = '#9aa1b2';
    ctx.font = '13px sans-serif';
    ctx.fillText('No queue data yet.', 8, 20);
    return;
  }

  names.forEach(name => {
    peakQueues[name] = Math.max(peakQueues[name] || 0, queues[name] || 0);
  });

  const peakValues = names.map(n => peakQueues[n]);
  const maxVal = Math.max(1, ...peakValues);
  const padding = 30;
  const chartH = h - padding;
  const barGap = 12;
  const barW = Math.max(20, (w - padding - barGap * names.length) / names.length);

  ctx.strokeStyle = '#2a2e3a';
  ctx.beginPath();
  ctx.moveTo(padding, 0);
  ctx.lineTo(padding, chartH);
  ctx.lineTo(w, chartH);
  ctx.stroke();

  names.forEach((name, i) => {
    const current = queues[name] || 0;
    const peak = peakQueues[name];
    const x = padding + barGap + i * (barW + barGap);

    // Faint bar = peak (persists through the spike so it doesn't vanish).
    const peakH = (peak / maxVal) * (chartH - 20);
    ctx.fillStyle = 'rgba(91, 140, 255, 0.25)';
    ctx.fillRect(x, chartH - peakH, barW, peakH);

    // Solid bar = current live value (can drop back to 0).
    const currentH = (current / maxVal) * (chartH - 20);
    ctx.fillStyle = '#5b8cff';
    ctx.fillRect(x, chartH - currentH, barW, currentH);

    ctx.fillStyle = '#e6e8ef';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${current} (peak ${peak})`, x + barW / 2, chartH - peakH - 4);
    ctx.fillStyle = '#9aa1b2';
    ctx.fillText(name, x + barW / 2, chartH + 16);
  });
  ctx.textAlign = 'left';
}

function renderProcessors(processors) {
  const tbody = document.querySelector('#processorTable tbody');
  const empty = document.getElementById('processorEmpty');
  tbody.innerHTML = '';
  const names = Object.keys(processors || {});
  empty.style.display = names.length === 0 ? 'block' : 'none';
  names.forEach(name => {
    const p = processors[name];
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${name}</td><td>${p.state}</td><td>${(p.utilization * 100).toFixed(0)}%</td>`;
    tbody.appendChild(tr);
  });
}

function renderRobots(robots) {
  const tbody = document.querySelector('#robotTable tbody');
  const empty = document.getElementById('robotEmpty');
  tbody.innerHTML = '';
  const names = Object.keys(robots || {});
  empty.style.display = names.length === 0 ? 'block' : 'none';
  names.forEach(name => {
    const r = robots[name];
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${name}</td><td>${r.x.toFixed(2)}</td><td>${r.y.toFixed(2)}</td><td>${r.speed.toFixed(2)}</td><td>${r.state}</td><td>${r.battery.toFixed(0)}%</td>`;
    tbody.appendChild(tr);
  });
}

async function poll() {
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  try {
    const res = await fetch('/api/v1/state', { cache: 'no-store' });
    const data = await res.json();

    if (!data.has_data) {
      dot.className = 'status-dot stale';
      text.textContent = 'No telemetry received yet';
      return;
    }

    dot.className = 'status-dot live';
    text.textContent = 'Live';

    document.getElementById('simTime').textContent = data.telemetry.simulation_time.toFixed(2);
    document.getElementById('modelStatus').textContent = data.telemetry.model_status;
    document.getElementById('receivedAt').textContent = data.received_at;

    const sources = data.telemetry.sources || {};
    const sinks = data.telemetry.sinks || {};
    document.getElementById('basketsIn').textContent =
      sources.BasketsIn ? sources.BasketsIn.count : '—';
    document.getElementById('basketsOut').textContent =
      sinks.BasketsOut ? sinks.BasketsOut.count : '—';

    drawBarChart(data.telemetry.queues || {});
    renderProcessors(data.telemetry.processors);
    renderRobots(data.telemetry.robots);
  } catch (err) {
    dot.className = 'status-dot stale';
    text.textContent = 'Bridge unreachable';
  }
}

document.getElementById('resetBtn').addEventListener('click', async () => {
  try {
    await fetch('/api/v1/state/reset', { method: 'POST' });
    peakQueues = {};
    document.getElementById('simTime').textContent = '—';
    document.getElementById('modelStatus').textContent = '—';
    document.getElementById('receivedAt').textContent = '—';
    document.getElementById('basketsIn').textContent = '—';
    document.getElementById('basketsOut').textContent = '—';
    drawBarChart({});
    renderProcessors({});
    renderRobots({});
    poll();
  } catch (err) {
    // best-effort; next poll() will surface "Bridge unreachable" if it's down
  }
});

poll();
setInterval(poll, POLL_MS);
</script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
def get_dashboard() -> HTMLResponse:
    return HTMLResponse(content=_DASHBOARD_HTML)
