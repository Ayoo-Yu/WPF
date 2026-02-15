const runsEl = document.getElementById("runs");
const leaderboardEl = document.getElementById("leaderboard");
const metricsEl = document.getElementById("metrics");
const leaderboardChartEl = document.getElementById("leaderboardChart");
const maeChartEl = document.getElementById("maeChart");
const rmseChartEl = document.getElementById("rmseChart");
const siteFilterEl = document.getElementById("siteFilter");
const logEl = document.getElementById("runLog");
const configInput = document.getElementById("configPath");
const runBtn = document.getElementById("runBtn");
const refreshBtn = document.getElementById("refreshBtn");

let currentRunId = null;
const state = {
  leaderboardRows: [],
  metricRows: [],
  selectedSite: "ALL",
};

function setLog(message, isError = false) {
  logEl.textContent = message;
  logEl.classList.toggle("error", isError);
}

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function renderTable(target, rows) {
  if (!rows || rows.length === 0) {
    target.innerHTML = "<p>暂无数据</p>";
    return;
  }

  const cols = Object.keys(rows[0]);
  const thead = `<thead><tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${rows
    .map((r) => `<tr>${cols.map((c) => `<td>${r[c] ?? ""}</td>`).join("")}</tr>`)
    .join("")}</tbody>`;
  target.innerHTML = `<table>${thead}${tbody}</table>`;
}

function renderBarChart(container, rows) {
  if (!rows.length) {
    container.innerHTML = "<p>暂无图表数据</p>";
    return;
  }

  const width = 680;
  const height = 220;
  const pad = { top: 16, right: 18, bottom: 36, left: 42 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const vals = rows.map((r) => toNum(r.avg_MAE));
  const ymax = Math.max(...vals) || 1;
  const barW = innerW / rows.length;

  let bars = "";
  let labels = "";
  rows.forEach((r, i) => {
    const x = pad.left + i * barW + 8;
    const v = toNum(r.avg_MAE);
    const h = (v / ymax) * innerH;
    const y = pad.top + (innerH - h);
    const label = String(r.model_name || "-");
    bars += `<rect x="${x}" y="${y}" width="${Math.max(barW - 16, 8)}" height="${h}" fill="#0f766e" rx="4"/>`;
    labels += `<text x="${x + Math.max(barW - 16, 8) / 2}" y="${height - 14}" text-anchor="middle" font-size="10" fill="#2b425c">${label}</text>`;
  });

  const svg = `
    <svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="avg MAE bar chart">
      <line x1="${pad.left}" y1="${pad.top + innerH}" x2="${width - pad.right}" y2="${pad.top + innerH}" stroke="#9eb0c4" />
      <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${pad.top + innerH}" stroke="#9eb0c4" />
      ${bars}
      ${labels}
      <text x="${pad.left}" y="${pad.top - 4}" font-size="10" fill="#2b425c">avg_MAE</text>
    </svg>
  `;
  container.innerHTML = svg;
}

function renderLineChart(container, metricRows, metricKey) {
  if (!metricRows.length) {
    container.innerHTML = "<p>暂无图表数据</p>";
    return;
  }

  const width = 680;
  const height = 220;
  const pad = { top: 16, right: 16, bottom: 30, left: 40 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const palette = ["#0f766e", "#0284c7", "#ca8a04", "#be123c", "#7c3aed"];

  const grouped = {};
  metricRows.forEach((r) => {
    const model = String(r.model_name || "unknown");
    if (!grouped[model]) grouped[model] = [];
    grouped[model].push({ x: toNum(r.horizon), y: toNum(r[metricKey]) });
  });

  const horizons = [...new Set(metricRows.map((r) => toNum(r.horizon)))].sort((a, b) => a - b);
  const allY = metricRows.map((r) => toNum(r[metricKey]));
  const ymax = Math.max(...allY) || 1;
  const xmin = Math.min(...horizons);
  const xmax = Math.max(...horizons);
  const xRange = Math.max(xmax - xmin, 1);

  const xScale = (x) => pad.left + ((x - xmin) / xRange) * innerW;
  const yScale = (y) => pad.top + (1 - y / ymax) * innerH;

  const lines = [];
  const dots = [];
  const legend = [];

  Object.entries(grouped).forEach(([model, points], i) => {
    points.sort((a, b) => a.x - b.x);
    const color = palette[i % palette.length];
    const d = points.map((p, idx) => `${idx === 0 ? "M" : "L"}${xScale(p.x)},${yScale(p.y)}`).join(" ");
    lines.push(`<path d="${d}" fill="none" stroke="${color}" stroke-width="2"/>`);
    points.forEach((p) => {
      dots.push(`<circle cx="${xScale(p.x)}" cy="${yScale(p.y)}" r="2.8" fill="${color}"/>`);
    });
    legend.push(`<span class="legend-item"><span class="legend-dot" style="background:${color}"></span>${model}</span>`);
  });

  const xTicks = horizons
    .map((h) => `<text x="${xScale(h)}" y="${height - 8}" text-anchor="middle" font-size="10" fill="#2b425c">${h}</text>`)
    .join("");

  const svg = `
    <svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="${metricKey} line chart">
      <line x1="${pad.left}" y1="${pad.top + innerH}" x2="${width - pad.right}" y2="${pad.top + innerH}" stroke="#9eb0c4" />
      <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${pad.top + innerH}" stroke="#9eb0c4" />
      ${lines.join("")}
      ${dots.join("")}
      ${xTicks}
      <text x="${pad.left}" y="${pad.top - 4}" font-size="10" fill="#2b425c">${metricKey}</text>
    </svg>
    <div class="legend">${legend.join("")}</div>
  `;

  container.innerHTML = svg;
}

function listSites(rowsA, rowsB) {
  const s = new Set(["ALL"]);
  rowsA.forEach((r) => s.add(String(r.site_id)));
  rowsB.forEach((r) => s.add(String(r.site_id)));
  return [...s];
}

function updateSiteFilter() {
  const sites = listSites(state.leaderboardRows, state.metricRows);
  const current = sites.includes(state.selectedSite) ? state.selectedSite : "ALL";
  siteFilterEl.innerHTML = sites.map((s) => `<option value="${s}">${s === "ALL" ? "全部" : s}</option>`).join("");
  siteFilterEl.value = current;
  state.selectedSite = current;
}

function renderCurrentView() {
  const selected = state.selectedSite;
  const lbRows =
    selected === "ALL" ? state.leaderboardRows : state.leaderboardRows.filter((r) => String(r.site_id) === selected);
  const mtRows = selected === "ALL" ? state.metricRows : state.metricRows.filter((r) => String(r.site_id) === selected);

  renderTable(leaderboardEl, lbRows);
  renderTable(metricsEl, mtRows.slice(0, 100));
  renderBarChart(leaderboardChartEl, lbRows);
  renderLineChart(maeChartEl, mtRows, "MAE");
  renderLineChart(rmseChartEl, mtRows, "RMSE");
}

async function fetchJson(url, options = {}) {
  const resp = await fetch(url, options);
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.error || `Request failed: ${resp.status}`);
  }
  return data;
}

async function loadRuns() {
  try {
    const data = await fetchJson("/api/runs");
    const runs = data.runs || [];
    if (runs.length === 0) {
      runsEl.innerHTML = "<p>还没有运行记录，先点击“运行 Demo”。</p>";
      leaderboardEl.innerHTML = "<p>暂无数据</p>";
      metricsEl.innerHTML = "<p>暂无数据</p>";
      leaderboardChartEl.innerHTML = "<p>暂无图表数据</p>";
      maeChartEl.innerHTML = "<p>暂无图表数据</p>";
      rmseChartEl.innerHTML = "<p>暂无图表数据</p>";
      return;
    }

    runsEl.innerHTML = runs
      .map(
        (r) => `
        <div class="run-item">
          <div><strong>${r.run_id}</strong></div>
          <div>实验: ${r.experiment || "-"}</div>
          <div>数据版本: ${r.dataset_version || "-"}</div>
          <button data-run-id="${r.run_id}">查看结果</button>
        </div>
      `
      )
      .join("");

    document.querySelectorAll(".run-item button").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const runId = btn.getAttribute("data-run-id");
        if (!runId) return;
        await loadRunResult(runId);
      });
    });

    if (!currentRunId) {
      await loadRunResult(runs[0].run_id);
    }
  } catch (err) {
    setLog(`加载运行记录失败: ${err.message}`, true);
  }
}

async function loadRunResult(runId) {
  try {
    currentRunId = runId;
    const [leaderboardData, metricsData] = await Promise.all([
      fetchJson(`/api/leaderboard?run_id=${encodeURIComponent(runId)}`),
      fetchJson(`/api/metrics?run_id=${encodeURIComponent(runId)}`),
    ]);

    state.leaderboardRows = leaderboardData.rows || [];
    state.metricRows = metricsData.rows || [];

    updateSiteFilter();
    renderCurrentView();
    setLog(`当前查看: ${runId}`);
  } catch (err) {
    setLog(`加载运行结果失败: ${err.message}`, true);
  }
}

siteFilterEl.addEventListener("change", () => {
  state.selectedSite = siteFilterEl.value;
  renderCurrentView();
});

runBtn.addEventListener("click", async () => {
  runBtn.disabled = true;
  setLog("正在运行 demo，请稍候...");
  try {
    const payload = { config_path: configInput.value.trim() || "configs/experiments/demo.yaml" };
    const data = await fetchJson("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setLog(data.stdout || data.message || "运行完成");
    currentRunId = null;
    await loadRuns();
  } catch (err) {
    setLog(`运行失败: ${err.message}`, true);
  } finally {
    runBtn.disabled = false;
  }
});

refreshBtn.addEventListener("click", loadRuns);

loadRuns();
