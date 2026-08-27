"""Live dashboard for visualizing the latest FlexSim telemetry, alongside
the real/ROS2-side environment for digital-twin comparison.

Self-contained HTML/JS page (no external assets, no build step) that polls
GET /api/v1/state and GET /api/v1/real/state on an interval and renders
queue levels, processor state, throughput counters, robots, and a
side-by-side FlexSim-vs-real comparison, plus a control to change the
real-environment robot fleet size live.
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
    color-scheme: light;
    --bg: #f2f4f8;
    --panel: #ffffff;
    --panel-2: #f8f9fc;
    --border: #e2e5ec;
    --text: #171a21;
    --muted: #6b7280;
    --accent: #3b6fe0;
    --accent-2: #7c5cff;
    --ok: #16a34a;
    --bad: #dc2626;
    --shadow: 0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06);
    --shadow-lg: 0 4px 12px rgba(16, 24, 40, 0.08), 0 2px 4px rgba(16, 24, 40, 0.04);
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --bg: #0b0d12;
    --panel: #14171f;
    --panel-2: #191c26;
    --border: #262a36;
    --text: #e8eaf0;
    --muted: #8b93a5;
    --accent: #6d93ff;
    --accent-2: #a78bfa;
    --ok: #34d17c;
    --bad: #f36565;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.4);
  }
  * { box-sizing: border-box; }
  html, body { max-width: 100%; overflow-x: hidden; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    -webkit-font-smoothing: antialiased;
  }
  .page { max-width: 1280px; margin: 0 auto; padding: 28px 28px 56px; }

  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 24px;
  }
  .brand { display: flex; align-items: center; gap: 12px; }
  .brand-mark {
    width: 36px; height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
    box-shadow: var(--shadow);
  }
  h1 { font-size: 17px; font-weight: 650; margin: 0; letter-spacing: -0.01em; }
  .sub { color: var(--muted); font-size: 12.5px; margin-top: 2px; }
  .status-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    margin-right: 6px;
    background: var(--muted);
  }
  .status-dot.live { background: var(--ok); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ok) 20%, transparent); }
  .status-dot.stale { background: var(--bad); }

  .topbar-actions { display: flex; gap: 8px; }
  button {
    font-family: inherit;
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    box-shadow: var(--shadow);
    transition: border-color 0.15s ease, transform 0.05s ease;
  }
  button:hover { border-color: var(--accent); }
  button:active { transform: scale(0.97); }
  button.primary {
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    color: white;
    border: none;
  }
  button.primary:hover { filter: brightness(1.08); }

  .section-title {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    font-weight: 650;
    margin: 32px 0 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .section-title:first-of-type { margin-top: 0; }
  .section-title .line { flex: 1; height: 1px; background: var(--border); }

  .stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .stat {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: var(--shadow);
  }
  .stat .label { color: var(--muted); font-size: 11.5px; font-weight: 550; text-transform: uppercase; letter-spacing: 0.03em; }
  .stat .value { font-size: 24px; font-weight: 650; margin-top: 6px; letter-spacing: -0.01em; }

  .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 14px; align-items: start; }
  .grid.even { grid-template-columns: 1fr 1fr; }
  @media (max-width: 860px) {
    .grid, .grid.even { grid-template-columns: 1fr; }
  }

  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: var(--shadow);
    margin-top: 14px;
  }
  .panel:first-child { margin-top: 0; }
  .panel h2 {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 6px;
    font-size: 13px;
    font-weight: 650;
    margin: 0 0 14px;
    letter-spacing: -0.005em;
  }
  .panel h2 .hint { font-weight: 450; color: var(--muted); font-size: 11.5px; margin-left: 0; }

  canvas { width: 100%; height: 250px; display: block; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 8px 8px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 550; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.02em; }
  tr:last-child td { border-bottom: none; }
  .empty { color: var(--muted); font-size: 13px; padding: 10px 2px; }

  .control-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 14px;
  }
  .control-row label { font-size: 12.5px; color: var(--muted); font-weight: 550; }
  .control-row input[type="number"] {
    width: 70px;
    font-family: inherit;
    font-size: 14px;
    padding: 6px 10px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--panel);
    color: var(--text);
  }
  .control-row .badge {
    font-size: 12px;
    color: var(--muted);
    margin-left: auto;
  }
  .control-row .badge b { color: var(--text); }

  .pill {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 600;
  }
  .pill.growing { background: color-mix(in srgb, var(--bad) 15%, transparent); color: var(--bad); }
  .pill.shrinking { background: color-mix(in srgb, var(--ok) 15%, transparent); color: var(--ok); }
  .pill.stable { background: color-mix(in srgb, var(--muted) 18%, transparent); color: var(--muted); }
</style>
</head>
<body>
<div class="page">

  <div class="topbar">
    <div class="brand">
      <div class="brand-mark">🏭</div>
      <div>
        <h1>FlexSim Digital Twin Bridge</h1>
        <div class="sub"><span id="statusDot" class="status-dot"></span><span id="statusText">connecting...</span></div>
      </div>
    </div>
    <div class="topbar-actions">
      <button id="themeBtn" title="Toggle light/dark theme">🌙 Dark</button>
      <button id="resetBtn" title="Clear stored telemetry so you can see fresh data arrive on the next run">Reset</button>
    </div>
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
      <div class="value" id="receivedAt" style="font-size:13px;">—</div>
    </div>
    <div class="stat" style="border-left: 3px solid var(--ok);">
      <div class="label">Baskets In</div>
      <div class="value" id="basketsIn" style="color: var(--ok);">—</div>
    </div>
    <div class="stat" style="border-left: 3px solid var(--accent);">
      <div class="label">Baskets Out</div>
      <div class="value" id="basketsOut" style="color: var(--accent);">—</div>
    </div>
  </div>

  <div class="section-title">FlexSim Simulation<div class="line"></div></div>

  <div class="grid">
    <div class="panel">
      <h2>Queue Levels<span class="hint">solid = current · faint = peak</span></h2>
      <canvas id="queueChart"></canvas>
    </div>
    <div class="panel">
      <h2>Processors</h2>
      <table id="processorTable"><thead><tr><th>Name</th><th>State</th><th>Util.</th></tr></thead><tbody></tbody></table>
      <div id="processorEmpty" class="empty" style="display:none;">No processor data yet.</div>
    </div>
  </div>

  <div class="grid even" style="margin-top:14px;">
    <div class="panel">
      <h2>Entry Points (In)</h2>
      <canvas id="entryChart"></canvas>
    </div>
    <div class="panel">
      <h2>Exit Points (Out)</h2>
      <canvas id="exitChart"></canvas>
    </div>
  </div>

  <div class="panel">
    <h2>Robots / AGVs</h2>
    <table id="robotTable"><thead><tr><th>Name</th><th>X</th><th>Y</th><th>Speed</th><th>State</th><th>Battery</th></tr></thead><tbody></tbody></table>
    <div id="robotEmpty" class="empty" style="display:none;">No robot data yet.</div>
  </div>

  <div class="section-title">Digital Twin Comparison — FlexSim vs Real / ROS2<div class="line"></div></div>

  <div class="panel">
    <div class="sub" style="margin-bottom:14px;">
      <span id="realStatusDot" class="status-dot"></span><span id="realStatusText">real environment: connecting...</span>
    </div>

    <div class="control-row">
      <label for="robotCountInput">Real-environment fleet size</label>
      <input type="number" id="robotCountInput" min="0" max="20" value="2" />
      <button class="primary" id="applyFleetBtn">Apply</button>
      <span class="badge">active robots: <b id="activeRobotCount">—</b></span>
    </div>

    <div class="stat-row" style="margin-bottom:14px;">
      <div class="stat">
        <div class="label">Backlog (Real Queue1+Queue2)</div>
        <div class="value" id="backlogValue">—</div>
      </div>
      <div class="stat">
        <div class="label">Trend</div>
        <div class="value" style="font-size:15px;"><span id="backlogTrend" class="pill stable">—</span></div>
      </div>
    </div>

    <h2>Queue Comparison<span class="hint">FlexSim vs Real, per queue</span></h2>
    <canvas id="comparisonChart"></canvas>

    <h2 style="margin-top:20px;">Real Robots (ROS2-side)</h2>
    <table id="realRobotTable"><thead><tr><th>Name</th><th>X</th><th>Y</th><th>Speed</th><th>State</th><th>Battery</th></tr></thead><tbody></tbody></table>
    <div id="realRobotEmpty" class="empty" style="display:none;">No real-robot data yet.</div>
  </div>

  <div class="section-title">RMS Scheduling Decision<div class="line"></div></div>

  <div class="panel">
    <div class="sub" style="margin-bottom:14px;">
      <span id="rmsStatusDot" class="status-dot"></span><span id="rmsStatusText">rms: no decision yet</span>
    </div>
    <div id="rmsDecisionBody" style="display:none;">
      <div class="stat-row" style="margin-bottom:14px;">
        <div class="stat">
          <div class="label">Mission</div>
          <div class="value" id="rmsMission" style="font-size:15px;">—</div>
        </div>
        <div class="stat">
          <div class="label">Selected Robot</div>
          <div class="value" id="rmsRobot" style="color: var(--accent);">—</div>
        </div>
        <div class="stat">
          <div class="label">Score</div>
          <div class="value" id="rmsScore">—</div>
        </div>
        <div class="stat">
          <div class="label">Command ID</div>
          <div class="value" id="rmsCommandId" style="font-size:12px;">—</div>
        </div>
      </div>
      <table id="rmsBreakdownTable">
        <thead><tr><th>travel_cost</th><th>battery_penalty</th><th>queue_cost</th><th>utilization_cost</th><th>priority_penalty</th></tr></thead>
        <tbody><tr>
          <td id="rmsTravel">—</td><td id="rmsBattery">—</td><td id="rmsQueue">—</td>
          <td id="rmsUtilization">—</td><td id="rmsPriority">—</td>
        </tr></tbody>
      </table>
      <div id="rmsFallbackNote" class="hint" style="display:none; margin-top:8px;">
        Fallback: no AVAILABLE robot found; assigned from the full candidate pool.
      </div>
    </div>
    <div id="rmsEmpty" class="empty">
      No decision posted yet. Run <code>examples/live_flexsim_rms_demo.py</code>
      (or anything posting to POST /api/v1/rms/decision) to see one here.
    </div>
  </div>

</div>

<script>
const POLL_MS = 1000;
const canvas = document.getElementById('queueChart');
const ctx = canvas.getContext('2d');
const entryCanvas = document.getElementById('entryChart');
const entryCtx = entryCanvas.getContext('2d');
const exitCanvas = document.getElementById('exitChart');
const exitCtx = exitCanvas.getContext('2d');
const comparisonCanvas = document.getElementById('comparisonChart');
const comparisonCtx = comparisonCanvas.getContext('2d');

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('themeBtn').textContent = theme === 'dark' ? '🌙 Dark' : '☀️ Light';
  try { localStorage.setItem('theme', theme); } catch (err) { /* ignore */ }
  drawBarChart(lastQueues);
  drawSimpleChart(entryCanvas, entryCtx, lastEntry, cssVar('--ok'));
  drawSimpleChart(exitCanvas, exitCtx, lastExit, cssVar('--accent'));
  drawComparisonChart(lastFlexQueues, lastRealQueues);
}

let lastQueues = {};
let lastEntry = {};
let lastExit = {};
let lastFlexQueues = {};
let lastRealQueues = {};

(function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem('theme'); } catch (err) { /* ignore */ }
  applyTheme(saved === 'light' ? 'light' : 'dark');
})();

document.getElementById('themeBtn').addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  applyTheme(current === 'dark' ? 'light' : 'dark');
});

function sizeCanvas(el, ctxRef) {
  const rect = el.getBoundingClientRect();
  el.width = rect.width * devicePixelRatio;
  el.height = rect.height * devicePixelRatio;
  ctxRef.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
}

function resizeCanvas() {
  sizeCanvas(canvas, ctx);
  sizeCanvas(entryCanvas, entryCtx);
  sizeCanvas(exitCanvas, exitCtx);
  sizeCanvas(comparisonCanvas, comparisonCtx);
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

// Tracks the highest value seen per queue since the last Reset, so a
// brief spike (item arrives then immediately leaves) stays visible
// instead of the bar collapsing back to 0 before anyone can see it.
let peakQueues = {};

function drawBarChart(queues) {
  lastQueues = queues;
  const rect = canvas.getBoundingClientRect();
  const w = rect.width, h = rect.height;
  ctx.clearRect(0, 0, w, h);

  const textColor = cssVar('--text');
  const mutedColor = cssVar('--muted');
  const borderColor = cssVar('--border');
  const accentColor = cssVar('--accent');

  const names = Object.keys(queues);
  if (names.length === 0) {
    ctx.fillStyle = mutedColor;
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

  ctx.strokeStyle = borderColor;
  ctx.beginPath();
  ctx.moveTo(padding, 0);
  ctx.lineTo(padding, chartH);
  ctx.lineTo(w, chartH);
  ctx.stroke();

  names.forEach((name, i) => {
    const current = queues[name] || 0;
    const peak = peakQueues[name];
    const x = padding + barGap + i * (barW + barGap);

    const peakH = (peak / maxVal) * (chartH - 20);
    ctx.fillStyle = accentColor + '40';
    ctx.fillRect(x, chartH - peakH, barW, peakH);

    const currentH = (current / maxVal) * (chartH - 20);
    ctx.fillStyle = accentColor;
    ctx.fillRect(x, chartH - currentH, barW, currentH);

    ctx.fillStyle = textColor;
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${current} (peak ${peak})`, x + barW / 2, chartH - peakH - 4);
    ctx.fillStyle = mutedColor;
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

// Simple live bar chart for monotonically-increasing throughput counters
// (entry/exit points): no peak-tracking needed since these never drop,
// so watching the bars grow between polls already reads as "dynamic".
function drawSimpleChart(el, ctxRef, points, color) {
  const rect = el.getBoundingClientRect();
  const w = rect.width, h = rect.height;
  ctxRef.clearRect(0, 0, w, h);

  const textColor = cssVar('--text');
  const mutedColor = cssVar('--muted');
  const borderColor = cssVar('--border');

  const names = Object.keys(points || {});
  if (names.length === 0) {
    ctxRef.fillStyle = mutedColor;
    ctxRef.font = '13px sans-serif';
    ctxRef.fillText('No data yet.', 8, 20);
    return;
  }

  const values = names.map(n => points[n].count || 0);
  const maxVal = Math.max(1, ...values);
  const padding = 30;
  const chartH = h - padding;
  const barGap = 10;
  const barW = Math.max(14, (w - padding - barGap * names.length) / names.length);

  ctxRef.strokeStyle = borderColor;
  ctxRef.beginPath();
  ctxRef.moveTo(padding, 0);
  ctxRef.lineTo(padding, chartH);
  ctxRef.lineTo(w, chartH);
  ctxRef.stroke();

  names.forEach((name, i) => {
    const val = values[i];
    const barH = (val / maxVal) * (chartH - 20);
    const x = padding + barGap + i * (barW + barGap);
    const y = chartH - barH;

    ctxRef.fillStyle = color;
    ctxRef.fillRect(x, y, barW, barH);

    ctxRef.fillStyle = textColor;
    ctxRef.font = '11px sans-serif';
    ctxRef.textAlign = 'center';
    ctxRef.fillText(String(val), x + barW / 2, y - 4);
    ctxRef.fillStyle = mutedColor;
    ctxRef.save();
    ctxRef.translate(x + barW / 2, chartH + 10);
    ctxRef.rotate(-Math.PI / 4);
    ctxRef.textAlign = 'right';
    ctxRef.fillText(name, 0, 0);
    ctxRef.restore();
  });
  ctxRef.textAlign = 'left';
}

// Grouped bar chart: for each queue name present in either source, draw
// a FlexSim bar and a Real/ROS2 bar side by side so the two can be
// compared directly: the core "digital twin" view.
function drawComparisonChart(flexQueues, realQueues) {
  lastFlexQueues = flexQueues;
  lastRealQueues = realQueues;
  const rect = comparisonCanvas.getBoundingClientRect();
  const w = rect.width, h = rect.height;
  comparisonCtx.clearRect(0, 0, w, h);

  const textColor = cssVar('--text');
  const mutedColor = cssVar('--muted');
  const borderColor = cssVar('--border');
  const flexColor = cssVar('--accent');
  const realColor = cssVar('--ok');

  const names = Array.from(new Set([...Object.keys(flexQueues || {}), ...Object.keys(realQueues || {})])).sort();
  if (names.length === 0) {
    comparisonCtx.fillStyle = mutedColor;
    comparisonCtx.font = '13px sans-serif';
    comparisonCtx.fillText('No comparable queue data yet.', 8, 20);
    return;
  }

  const allValues = names.flatMap(n => [flexQueues[n] || 0, realQueues[n] || 0]);
  const maxVal = Math.max(1, ...allValues);
  const padding = 30;
  const topPadding = 26; // room for the legend row + tallest bar's value label, so neither overlaps the other
  const chartH = h - padding;
  const groupGap = 24;
  const barGap = 4;
  const groupW = Math.max(40, (w - padding - groupGap * names.length) / names.length);
  const barW = (groupW - barGap) / 2;

  comparisonCtx.strokeStyle = borderColor;
  comparisonCtx.beginPath();
  comparisonCtx.moveTo(padding, 0);
  comparisonCtx.lineTo(padding, chartH);
  comparisonCtx.lineTo(w, chartH);
  comparisonCtx.stroke();

  names.forEach((name, i) => {
    const flexVal = flexQueues[name] || 0;
    const realVal = realQueues[name] || 0;
    const groupX = padding + groupGap + i * (groupW + groupGap);

    const flexH = (flexVal / maxVal) * (chartH - topPadding);
    comparisonCtx.fillStyle = flexColor;
    comparisonCtx.fillRect(groupX, chartH - flexH, barW, flexH);
    comparisonCtx.fillStyle = textColor;
    comparisonCtx.font = '11px sans-serif';
    comparisonCtx.textAlign = 'center';
    comparisonCtx.fillText(String(flexVal), groupX + barW / 2, chartH - flexH - 4);

    const realH = (realVal / maxVal) * (chartH - topPadding);
    const realX = groupX + barW + barGap;
    comparisonCtx.fillStyle = realColor;
    comparisonCtx.fillRect(realX, chartH - realH, barW, realH);
    comparisonCtx.fillStyle = textColor;
    comparisonCtx.fillText(String(realVal), realX + barW / 2, chartH - realH - 4);

    comparisonCtx.fillStyle = mutedColor;
    comparisonCtx.fillText(name, groupX + groupW / 2, chartH + 16);
  });
  comparisonCtx.textAlign = 'left';

  comparisonCtx.fillStyle = flexColor;
  comparisonCtx.fillRect(padding, 4, 10, 10);
  comparisonCtx.fillStyle = textColor;
  comparisonCtx.font = '11px sans-serif';
  comparisonCtx.fillText('FlexSim', padding + 16, 13);
  comparisonCtx.fillStyle = realColor;
  comparisonCtx.fillRect(padding + 80, 4, 10, 10);
  comparisonCtx.fillStyle = textColor;
  comparisonCtx.fillText('Real / ROS2', padding + 96, 13);
}

function sumCounts(points) {
  return Object.values(points || {}).reduce((total, p) => total + (p.count || 0), 0);
}

// Display-only relabeling (e.g. "TaskExecuter3" -> "Robot 3"). The
// underlying telemetry keys are left untouched; this only affects what's
// shown in the table.
function robotDisplayName(name) {
  const match = name.match(/^TaskExecuter(\\d+)$/i);
  return match ? `Robot ${match[1]}` : name;
}

function renderRobots(tableId, emptyId, robots) {
  const tbody = document.querySelector(`#${tableId} tbody`);
  const empty = document.getElementById(emptyId);
  tbody.innerHTML = '';
  const names = Object.keys(robots || {});
  empty.style.display = names.length === 0 ? 'block' : 'none';
  names.forEach(name => {
    const r = robots[name];
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${robotDisplayName(name)}</td><td>${r.x.toFixed(2)}</td><td>${r.y.toFixed(2)}</td><td>${r.speed.toFixed(2)}</td><td>${r.state}</td><td>${r.battery.toFixed(0)}%</td>`;
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
    document.getElementById('basketsIn').textContent = sumCounts(sources);
    document.getElementById('basketsOut').textContent = sumCounts(sinks);
    lastEntry = sources;
    lastExit = sinks;
    drawSimpleChart(entryCanvas, entryCtx, sources, cssVar('--ok'));
    drawSimpleChart(exitCanvas, exitCtx, sinks, cssVar('--accent'));

    drawBarChart(data.telemetry.queues || {});
    renderProcessors(data.telemetry.processors);
    renderRobots('robotTable', 'robotEmpty', data.telemetry.robots);

    lastFlexQueues = data.telemetry.queues || {};
    drawComparisonChart(lastFlexQueues, lastRealQueues);
  } catch (err) {
    dot.className = 'status-dot stale';
    text.textContent = 'Bridge unreachable';
  }
}

let prevBacklog = null;

// Rolling history of backlog readings, used to smooth out the trend
// indicator. A single-tick comparison is too noisy (random tote arrivals
// make it flicker between growing/shrinking/stable every second even
// when the real trend is clearly one direction), so instead we compare the
// average of the first half of the window against the second half.
const BACKLOG_HISTORY_SIZE = 20; // ~20s at 1 poll/sec
let backlogHistory = [];

function updateBacklog(queues) {
  const backlog = (queues.Queue1 || 0) + (queues.Queue2 || 0);
  document.getElementById('backlogValue').textContent = backlog;

  backlogHistory.push(backlog);
  if (backlogHistory.length > BACKLOG_HISTORY_SIZE) backlogHistory.shift();

  const trendEl = document.getElementById('backlogTrend');
  if (backlogHistory.length < 6) {
    trendEl.textContent = '… warming up';
    trendEl.className = 'pill stable';
    prevBacklog = backlog;
    return;
  }

  const mid = Math.floor(backlogHistory.length / 2);
  const firstHalfAvg = backlogHistory.slice(0, mid).reduce((a, b) => a + b, 0) / mid;
  const secondHalfAvg = backlogHistory.slice(mid).reduce((a, b) => a + b, 0) / (backlogHistory.length - mid);
  const delta = secondHalfAvg - firstHalfAvg;
  const NOISE_THRESHOLD = 0.5; // totes; ignore sub-tote drift as "stable"

  if (Math.abs(delta) < NOISE_THRESHOLD) {
    trendEl.textContent = '— stable';
    trendEl.className = 'pill stable';
  } else if (delta > 0) {
    trendEl.textContent = `↑ growing (+${delta.toFixed(1)}/${BACKLOG_HISTORY_SIZE}s)`;
    trendEl.className = 'pill growing';
  } else {
    trendEl.textContent = `↓ shrinking (${delta.toFixed(1)}/${BACKLOG_HISTORY_SIZE}s)`;
    trendEl.className = 'pill shrinking';
  }
  prevBacklog = backlog;
}

async function pollReal() {
  const dot = document.getElementById('realStatusDot');
  const text = document.getElementById('realStatusText');
  try {
    const res = await fetch('/api/v1/real/state', { cache: 'no-store' });
    const data = await res.json();

    if (!data.has_data) {
      dot.className = 'status-dot stale';
      text.textContent = 'real environment: no telemetry yet';
      lastRealQueues = {};
      renderRobots('realRobotTable', 'realRobotEmpty', {});
      document.getElementById('activeRobotCount').textContent = '—';
    } else {
      dot.className = 'status-dot live';
      text.textContent = `real environment: live (t=${data.telemetry.simulation_time.toFixed(0)}s)`;
      lastRealQueues = data.telemetry.queues || {};
      updateBacklog(lastRealQueues);
      const robots = data.telemetry.robots || {};
      renderRobots('realRobotTable', 'realRobotEmpty', robots);
      document.getElementById('activeRobotCount').textContent = Object.keys(robots).length;
    }
    drawComparisonChart(lastFlexQueues, lastRealQueues);
  } catch (err) {
    dot.className = 'status-dot stale';
    text.textContent = 'real environment: bridge unreachable';
  }
}

async function pollRms() {
  const dot = document.getElementById('rmsStatusDot');
  const text = document.getElementById('rmsStatusText');
  const body = document.getElementById('rmsDecisionBody');
  const empty = document.getElementById('rmsEmpty');
  try {
    const res = await fetch('/api/v1/rms/decision', { cache: 'no-store' });
    const data = await res.json();

    if (!data.has_data) {
      dot.className = 'status-dot stale';
      text.textContent = 'rms: no decision yet';
      body.style.display = 'none';
      empty.style.display = '';
      return;
    }

    const d = data.decision;
    dot.className = 'status-dot live';
    text.textContent = `rms: last decision at ${new Date(d.received_at).toLocaleTimeString()}`;
    body.style.display = '';
    empty.style.display = 'none';

    document.getElementById('rmsMission').textContent = `${d.mission_type} ${d.source} -> ${d.destination}`;
    document.getElementById('rmsRobot').textContent = d.selected_robot;
    document.getElementById('rmsScore').textContent = d.score.toFixed(2);
    document.getElementById('rmsCommandId').textContent = d.command_id;
    document.getElementById('rmsTravel').textContent = d.travel_cost.toFixed(2);
    document.getElementById('rmsBattery').textContent = d.battery_penalty.toFixed(2);
    document.getElementById('rmsQueue').textContent = d.queue_cost.toFixed(2);
    document.getElementById('rmsUtilization').textContent = d.utilization_cost.toFixed(2);
    document.getElementById('rmsPriority').textContent = d.priority_penalty.toFixed(2);
    document.getElementById('rmsFallbackNote').style.display = d.used_fallback ? '' : 'none';
  } catch (err) {
    dot.className = 'status-dot stale';
    text.textContent = 'rms: bridge unreachable';
  }
}

async function pollFleetConfig() {
  try {
    const res = await fetch('/api/v1/real/config', { cache: 'no-store' });
    const data = await res.json();
    const input = document.getElementById('robotCountInput');
    if (document.activeElement !== input) {
      input.value = data.robot_count;
    }
  } catch (err) {
    // best-effort
  }
}

document.getElementById('applyFleetBtn').addEventListener('click', async () => {
  const input = document.getElementById('robotCountInput');
  const robotCount = parseInt(input.value, 10);
  if (Number.isNaN(robotCount) || robotCount < 0 || robotCount > 20) return;
  try {
    await fetch('/api/v1/real/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ robot_count: robotCount }),
    });
  } catch (err) {
    // best-effort; pollFleetConfig() will resync the input on next tick
  }
});

document.getElementById('resetBtn').addEventListener('click', async () => {
  try {
    await fetch('/api/v1/state/reset', { method: 'POST' });
    await fetch('/api/v1/real/state/reset', { method: 'POST' });
    await fetch('/api/v1/rms/decision/reset', { method: 'POST' });
    peakQueues = {};
    document.getElementById('simTime').textContent = '—';
    document.getElementById('modelStatus').textContent = '—';
    document.getElementById('receivedAt').textContent = '—';
    document.getElementById('basketsIn').textContent = '—';
    document.getElementById('basketsOut').textContent = '—';
    drawBarChart({});
    renderProcessors({});
    renderRobots('robotTable', 'robotEmpty', {});
    renderRobots('realRobotTable', 'realRobotEmpty', {});
    prevBacklog = null;
    backlogHistory = [];
    document.getElementById('backlogValue').textContent = '—';
    document.getElementById('backlogTrend').textContent = '—';
    document.getElementById('backlogTrend').className = 'pill stable';
    drawSimpleChart(entryCanvas, entryCtx, {}, cssVar('--ok'));
    drawSimpleChart(exitCanvas, exitCtx, {}, cssVar('--accent'));
    lastFlexQueues = {};
    lastRealQueues = {};
    drawComparisonChart({}, {});
    poll();
    pollReal();
    pollRms();
  } catch (err) {
    // best-effort; next poll() will surface "Bridge unreachable" if it's down
  }
});

poll();
pollReal();
pollRms();
pollFleetConfig();
setInterval(poll, POLL_MS);
setInterval(pollReal, POLL_MS);
setInterval(pollRms, POLL_MS);
setInterval(pollFleetConfig, POLL_MS);
</script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
def get_dashboard() -> HTMLResponse:
    return HTMLResponse(content=_DASHBOARD_HTML)
