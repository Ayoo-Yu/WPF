const runsEl = document.getElementById("runs");
const leaderboardEl = document.getElementById("leaderboard");
const metricsEl = document.getElementById("metrics");
const leaderboardChartEl = document.getElementById("leaderboardChart");
const maeChartEl = document.getElementById("maeChart");
const rmseChartEl = document.getElementById("rmseChart");
const datasetProfileEl = document.getElementById("datasetProfile");
const failedModelsEl = document.getElementById("failedModels");
const stabilityEl = document.getElementById("stability");
const stabilityChartEl = document.getElementById("stabilityChart");
const siteFilterEl = document.getElementById("siteFilter");
const leaderMetricEl = document.getElementById("leaderMetric");
const segmentFilterEl = document.getElementById("segmentFilter");
const logEl = document.getElementById("runLog");
const toggleLogBtn = document.getElementById("toggleLogBtn");
const metricsHintEl = document.getElementById("metricsHint");
const configInput = document.getElementById("configPath");
const runBtn = document.getElementById("runBtn");
const refreshBtn = document.getElementById("refreshBtn");
const runStatusEl = document.getElementById("runStatus");
const runIdTextEl = document.getElementById("runIdText");
const runTimeTextEl = document.getElementById("runTimeText");
const modelSearchEl = document.getElementById("modelSearch");

const pageTabsEl = document.getElementById("pageTabs");
const configSelectEl = document.getElementById("configSelect");
const configPreviewEl = document.getElementById("configPreview");
const reloadConfigsBtn = document.getElementById("reloadConfigsBtn");
const useConfigBtn = document.getElementById("useConfigBtn");
const runSelectedConfigBtn = document.getElementById("runSelectedConfigBtn");
const reloadStorageBtn = document.getElementById("reloadStorageBtn");
const storageSummaryEl = document.getElementById("storageSummary");
const cleanupKeepLatestEl = document.getElementById("cleanupKeepLatest");
const cleanupPrefixEl = document.getElementById("cleanupPrefix");
const cleanupPreviewBtn = document.getElementById("cleanupPreviewBtn");
const cleanupExecuteBtn = document.getElementById("cleanupExecuteBtn");
const cleanupLogEl = document.getElementById("cleanupLog");
const reloadReportBtn = document.getElementById("reloadReportBtn");
const runSummaryEl = document.getElementById("runSummary");
const reportTextEl = document.getElementById("reportText");
const artifactsEl = document.getElementById("artifacts");
const downloadReportBtn = document.getElementById("downloadReportBtn");
const downloadLeaderboardBtn = document.getElementById("downloadLeaderboardBtn");
const downloadMetricsBtn = document.getElementById("downloadMetricsBtn");
const compareBaseRunEl = document.getElementById("compareBaseRun");
const compareTargetRunEl = document.getElementById("compareTargetRun");
const compareRunsBtn = document.getElementById("compareRunsBtn");
const compareResultEl = document.getElementById("compareResult");
const compareSegmentsEl = document.getElementById("compareSegments");
const reloadTrendBtn = document.getElementById("reloadTrendBtn");
const bestTrendEl = document.getElementById("bestTrend");

let currentRunId = null;
const state = {
  runs: [],
  configs: [],
  leaderboardRows: [],
  metricRows: [],
  stabilityRows: [],
  selectedSite: "ALL",
  leaderMetric: "avg_MAE",
  segmentFilter: "overall",
  modelSearch: "",
  tableExpanded: {
    leaderboard: false,
    metrics: false,
    failed: false,
    summary_models: false,
  },
  tableSort: {
    leaderboard: { key: "avg_MAE", dir: "asc" },
    metrics: { key: "MAE", dir: "asc" },
    failed: { key: "model_name", dir: "asc" },
    stability: { key: "cv_MAE", dir: "asc" },
    summary_models: { key: "label", dir: "asc" },
  },
  lastReportText: "",
};

function setLog(message, isError = false) {
  logEl.textContent = message;
  logEl.classList.toggle("error", isError);
}

function setStatus(kind, runId = "-") {
  const chip = runStatusEl.querySelector(".status-chip");
  chip.classList.remove("running", "error");
  if (kind === "running") {
    chip.textContent = "状态: 运行中";
    chip.classList.add("running");
  } else if (kind === "error") {
    chip.textContent = "状态: 失败";
    chip.classList.add("error");
  } else if (kind === "ready") {
    chip.textContent = "状态: 已完成";
  } else {
    chip.textContent = "状态: 待命";
  }
  runIdTextEl.textContent = `run_id: ${runId || "-"}`;
  runTimeTextEl.textContent = `更新时间: ${new Date().toLocaleString("zh-CN")}`;
}

function switchPage(page) {
  document.querySelectorAll(".page").forEach((el) => {
    el.classList.toggle("hidden", el.getAttribute("data-page") !== page);
  });
  pageTabsEl.querySelectorAll(".tab").forEach((el) => {
    el.classList.toggle("active", el.getAttribute("data-page") === page);
  });
}

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function shortText(v, maxLen = 42) {
  const s = String(v ?? "");
  if (s.length <= maxLen) return s;
  return `${s.slice(0, maxLen - 1)}…`;
}

function formatModelName(name) {
  const s = String(name || "-");
  const base = s.split("[")[0];
  const lag = s.match(/lags?=(\d+)/i);
  const win = s.match(/window=(\d+)/i);
  const parts = [base];
  if (lag) parts.push(`L${lag[1]}`);
  if (win) parts.push(`W${win[1]}`);
  return parts.join("-");
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function sortRows(rows, sortKey, sortDir) {
  if (!sortKey) return rows;
  return [...rows].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    const na = Number(av);
    const nb = Number(bv);
    let cmp = 0;
    if (Number.isFinite(na) && Number.isFinite(nb)) {
      cmp = na - nb;
    } else {
      cmp = String(av ?? "").localeCompare(String(bv ?? ""), "zh-CN");
    }
    return sortDir === "desc" ? -cmp : cmp;
  });
}

function renderTable(target, rows, opts = {}) {
  if (!rows || rows.length === 0) {
    target.innerHTML = '<p class="empty">暂无数据</p>';
    return;
  }

  const key = String(opts.key || "");
  const limit = Number(opts.limit || 0);
  const expanded = key ? !!state.tableExpanded[key] : false;
  const sortState = state.tableSort[key] || { key: "", dir: "asc" };
  const sortedRows = sortRows(rows, sortState.key, sortState.dir);
  const showRows = !limit || expanded ? sortedRows : sortedRows.slice(0, limit);

  const cols = Object.keys(sortedRows[0]);
  const th = cols
    .map((c) => {
      const isActive = sortState.key === c;
      const arrow = isActive ? (sortState.dir === "asc" ? " ▲" : " ▼") : "";
      const cls = c === "model_name" || c === "label" ? ' class="col-model"' : "";
      return `<th${cls}><button data-sort-table="${key}" data-sort-col="${c}">${c}${arrow}</button></th>`;
    })
    .join("");

  const tbody = showRows
    .map((r) => {
      const tds = cols
        .map((c) => {
          const value = r[c] ?? "";
          const raw = String(value);
          const shown =
            c === "model_name" || c === "label" ? shortText(formatModelName(raw), 28) : shortText(raw);
          const cls = c === "model_name" || c === "label" ? ' class="cell-model"' : "";
          return `<td${cls} title="${escapeHtml(raw)}">${escapeHtml(shown)}</td>`;
        })
        .join("");
      return `<tr>${tds}</tr>`;
    })
    .join("");

  const needToggle = !!limit && sortedRows.length > limit;
  const toggleText = expanded ? "收起" : `展开全部 (${sortedRows.length})`;

  target.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr>${th}</tr></thead>
        <tbody>${tbody}</tbody>
      </table>
    </div>
    ${
      needToggle
        ? `<div class="table-tools"><button data-table-toggle="${key}" class="ghost">${toggleText}</button></div>`
        : ""
    }
  `;

  target.querySelectorAll("[data-sort-table]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tableKey = btn.getAttribute("data-sort-table");
      const col = btn.getAttribute("data-sort-col");
      if (!tableKey || !col) return;
      const curr = state.tableSort[tableKey] || { key: "", dir: "asc" };
      const nextDir = curr.key === col && curr.dir === "asc" ? "desc" : "asc";
      state.tableSort[tableKey] = { key: col, dir: nextDir };
      renderCurrentView();
      renderRunSummary(state.lastSummary || {});
    });
  });

  if (needToggle) {
    const toggleBtn = target.querySelector(`[data-table-toggle="${key}"]`);
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        state.tableExpanded[key] = !state.tableExpanded[key];
        renderCurrentView();
        renderRunSummary(state.lastSummary || {});
      });
    }
  }
}

function renderHorizontalBarChart(container, rows, metricKey) {
  if (!rows.length) {
    container.innerHTML = '<p class="empty">暂无图表数据</p>';
    return;
  }

  const topRows = [...rows].sort((a, b) => toNum(a[metricKey]) - toNum(b[metricKey])).slice(0, 8);
  const width = 680;
  const rowH = 28;
  const height = Math.max(190, 40 + topRows.length * rowH);
  const pad = { top: 20, right: 44, bottom: 12, left: 190 };
  const innerW = width - pad.left - pad.right;

  const vals = topRows.map((r) => toNum(r[metricKey]));
  const max = Math.max(...vals, 0.0001);

  const bars = topRows
    .map((r, i) => {
      const value = toNum(r[metricKey]);
      const y = pad.top + i * rowH;
      const barW = (value / max) * innerW;
      const model = shortText(formatModelName(r.model_name), 20);
      return `
        <text x="${pad.left - 8}" y="${y + 16}" text-anchor="end" font-size="10" fill="#2b425c">${escapeHtml(model)}</text>
        <rect x="${pad.left}" y="${y + 5}" width="${barW}" height="16" fill="#0f766e" rx="4" />
        <text x="${pad.left + barW + 6}" y="${y + 17}" font-size="10" fill="#2b425c">${value.toFixed(4)}</text>
      `;
    })
    .join("");

  container.innerHTML = `
    <svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="leaderboard bar chart">
      <line x1="${pad.left}" y1="${pad.top - 2}" x2="${pad.left}" y2="${height - 12}" stroke="#9eb0c4" />
      <line x1="${pad.left}" y1="${height - 12}" x2="${width - pad.right}" y2="${height - 12}" stroke="#9eb0c4" />
      ${bars}
      <text x="${pad.left}" y="12" font-size="10" fill="#2b425c">${metricKey} (Top 8, 越低越好)</text>
    </svg>
  `;
}

function renderLineChart(container, metricRows, metricKey) {
  if (!metricRows.length) {
    container.innerHTML = '<p class="empty">暂无图表数据</p>';
    return;
  }

  const width = 680;
  const height = 220;
  const pad = { top: 16, right: 16, bottom: 30, left: 40 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const palette = ["#0f766e", "#0284c7", "#ca8a04", "#be123c", "#7c3aed", "#0d9488", "#334155"];

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
    legend.push(
      `<span class="legend-item" title="${escapeHtml(model)}"><span class="legend-dot" style="background:${color}"></span>${escapeHtml(shortText(formatModelName(model), 20))}</span>`
    );
  });

  const xTicks = horizons
    .map((h) => `<text x="${xScale(h)}" y="${height - 8}" text-anchor="middle" font-size="10" fill="#2b425c">${h}</text>`)
    .join("");

  container.innerHTML = `
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
}

function renderStabilityChart(container, rows) {
  if (!rows || rows.length === 0) {
    container.innerHTML = '<p class="empty">暂无稳定性图表数据</p>';
    return;
  }
  const topRows = [...rows].sort((a, b) => toNum(a.cv_MAE) - toNum(b.cv_MAE)).slice(0, 12);
  const width = 680;
  const height = 230;
  const pad = { top: 20, right: 16, bottom: 34, left: 44 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const xVals = topRows.map((r) => toNum(r.mean_MAE));
  const yVals = topRows.map((r) => toNum(r.cv_MAE));
  const xMin = Math.min(...xVals);
  const xMax = Math.max(...xVals);
  const yMax = Math.max(...yVals, 0.0001);
  const xRange = Math.max(xMax - xMin, 1e-6);
  const xScale = (x) => pad.left + ((x - xMin) / xRange) * innerW;
  const yScale = (y) => pad.top + (1 - y / yMax) * innerH;

  const dots = topRows
    .map((r) => {
      const cx = xScale(toNum(r.mean_MAE));
      const cy = yScale(toNum(r.cv_MAE));
      const label = shortText(formatModelName(r.model_name), 14);
      return `<circle cx="${cx}" cy="${cy}" r="4.4" fill="#155e75"><title>${escapeHtml(
        String(r.model_name)
      )}</title></circle><text x="${cx + 6}" y="${cy - 4}" font-size="9" fill="#2b425c">${escapeHtml(label)}</text>`;
    })
    .join("");

  container.innerHTML = `
    <svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="stability scatter chart">
      <line x1="${pad.left}" y1="${pad.top + innerH}" x2="${width - pad.right}" y2="${pad.top + innerH}" stroke="#9eb0c4" />
      <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${pad.top + innerH}" stroke="#9eb0c4" />
      ${dots}
      <text x="${pad.left}" y="${height - 8}" font-size="10" fill="#2b425c">mean_MAE (越左越好)</text>
      <text x="${pad.left}" y="${pad.top - 4}" font-size="10" fill="#2b425c">cv_MAE (越低越稳)</text>
    </svg>
  `;
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

function bySearch(rows) {
  if (!state.modelSearch) return rows;
  const kw = state.modelSearch.toLowerCase();
  return rows.filter((r) => String(r.model_name || "").toLowerCase().includes(kw));
}

function renderCurrentView() {
  const selected = state.selectedSite;
  const lbBase =
    selected === "ALL" ? state.leaderboardRows : state.leaderboardRows.filter((r) => String(r.site_id) === selected);
  const mtBase = selected === "ALL" ? state.metricRows : state.metricRows.filter((r) => String(r.site_id) === selected);

  const lbRows = bySearch(lbBase);
  const bySite = bySearch(mtBase);
  const mtRows = bySite.filter((r) => String(r.segment_key || "overall") === state.segmentFilter);
  const stBase =
    selected === "ALL" ? state.stabilityRows : state.stabilityRows.filter((r) => String(r.site_id) === selected);
  const stRows = bySearch(stBase);

  renderTable(leaderboardEl, lbRows, { key: "leaderboard", limit: 12 });
  renderTable(metricsEl, mtRows, { key: "metrics", limit: 24 });
  renderTable(stabilityEl, stRows, { key: "stability", limit: 12 });
  renderStabilityChart(stabilityChartEl, stRows);
  renderHorizontalBarChart(leaderboardChartEl, lbRows, state.leaderMetric);
  renderLineChart(maeChartEl, mtRows, "MAE");
  renderLineChart(rmseChartEl, mtRows, "RMSE");

  const showCount = state.tableExpanded.metrics ? mtRows.length : Math.min(mtRows.length, 24);
  metricsHintEl.textContent = `当前显示 ${showCount} / ${mtRows.length} 条`;
}

function renderProfile(profile) {
  if (!profile || Object.keys(profile).length === 0) {
    datasetProfileEl.innerHTML = '<p class="empty">暂无数据质量信息</p>';
    return;
  }
  const keys = [
    "site_id",
    "rows_scada",
    "rows_nwp",
    "rows_aligned",
    "rows_final",
    "rows_dropped_target_parse",
    "n_exog_features",
    "target_min",
    "target_max",
    "target_mean",
    "time_start",
    "time_end",
  ];
  const html = keys
    .filter((k) => profile[k] !== undefined)
    .map(
      (k) => `
      <div class="profile-item">
        <div class="k">${k}</div>
        <div class="v">${profile[k]}</div>
      </div>
    `
    )
    .join("");
  datasetProfileEl.innerHTML = `<div class="profile-grid">${html}</div>`;
}

function renderFailedModels(rows) {
  if (!rows || rows.length === 0) {
    failedModelsEl.innerHTML = '<p class="empty">无失败模型。</p>';
    return;
  }
  renderTable(failedModelsEl, rows, { key: "failed", limit: 10 });
}

function renderRunSummary(summary) {
  if (!summary || Object.keys(summary).length === 0) {
    runSummaryEl.innerHTML = '<p class="empty">暂无运行摘要。</p>';
    return;
  }

  const overview = [
    { key: "experiment", value: summary.experiment || "-" },
    { key: "dataset_version", value: summary.dataset_version || "-" },
    { key: "horizons", value: (summary.horizons || []).join(",") || "-" },
    { key: "sites", value: (summary.sites || []).join(",") || "-" },
    { key: "refit_each_origin", value: String(summary.refit_each_origin) },
    { key: "skip_failed_models", value: String(summary.skip_failed_models) },
    { key: "failed_models", value: String((summary.failed_models || []).length) },
  ];
  const cards = overview
    .map(
      (x) => `<div class="profile-item"><div class="k">${x.key}</div><div class="v">${escapeHtml(x.value)}</div></div>`
    )
    .join("");

  let modelsHtml = '<p class="empty">模型清单为空</p>';
  if (summary.models && summary.models.length) {
    const rows = summary.models.map((m) => ({
      name: m.name,
      label: m.label,
      params: JSON.stringify(m.params || {}),
    }));
    const tmp = document.createElement("div");
    renderTable(tmp, rows, { key: "summary_models", limit: 10 });
    modelsHtml = tmp.innerHTML;
  }

  runSummaryEl.innerHTML = `
    <div class="profile-grid">${cards}</div>
    <h3 style="margin-top:12px;">模型组合</h3>
    ${modelsHtml}
  `;
}

function renderReport(text) {
  reportTextEl.textContent = text || "暂无报告，请先运行包含 report.md 的实验。";
}

function renderArtifacts(rows) {
  if (!rows || rows.length === 0) {
    artifactsEl.innerHTML = '<p class="empty">暂无产物。</p>';
    return;
  }
  renderTable(artifactsEl, rows, { key: "artifacts", limit: 20 });
}

function bytesToHuman(n) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let v = Number(n) || 0;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

function setCleanupLog(payload) {
  cleanupLogEl.textContent = JSON.stringify(payload, null, 2);
}

async function loadStorageSummary() {
  try {
    const data = await fetchJson("/api/storage_summary");
    const rows = [
      { key: "run_count", value: data.run_count ?? 0 },
      { key: "total_size", value: bytesToHuman(data.total_bytes ?? 0) },
      { key: "oldest_run", value: data.oldest_run || "-" },
      { key: "newest_run", value: data.newest_run || "-" },
    ];
    renderTable(storageSummaryEl, rows, { key: "storage", limit: 10 });
  } catch (err) {
    storageSummaryEl.innerHTML = `<p class=\"error\">加载存储信息失败: ${escapeHtml(err.message)}</p>`;
  }
}

async function runCleanup(dryRun) {
  const keepLatest = Number(cleanupKeepLatestEl.value || "20");
  const prefix = cleanupPrefixEl.value.trim();
  const payload = {
    keep_latest: Number.isFinite(keepLatest) ? keepLatest : 20,
    prefix,
    dry_run: dryRun,
  };
  try {
    const data = await fetchJson("/api/cleanup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setCleanupLog(data);
    await loadStorageSummary();
    await loadRuns();
  } catch (err) {
    setCleanupLog({ error: String(err.message || err) });
  }
}

function aggregateBestBySegment(metricRows) {
  const grouped = {};
  (metricRows || []).forEach((r) => {
    const k = `${r.segment_key || ""}|${r.segment_value || ""}`;
    if (!grouped[k]) grouped[k] = [];
    grouped[k].push(r);
  });
  const rows = [];
  Object.entries(grouped).forEach(([k, arr]) => {
    const sorted = [...arr].sort((a, b) => toNum(a.MAE) - toNum(b.MAE));
    const best = sorted[0];
    const [segment_key, segment_value] = k.split("|");
    rows.push({
      segment_key,
      segment_value,
      best_model: best.model_name,
      best_MAE: Number(toNum(best.MAE).toFixed(6)),
    });
  });
  return rows.sort((a, b) => `${a.segment_key}_${a.segment_value}`.localeCompare(`${b.segment_key}_${b.segment_value}`));
}

function renderBestTrend(rows) {
  if (!rows || rows.length === 0) {
    bestTrendEl.innerHTML = '<p class="empty">暂无轨迹数据。</p>';
    return;
  }
  renderTable(bestTrendEl, rows, { key: "best_trend", limit: 20 });
}

async function loadBestTrend() {
  try {
    const data = await fetchJson("/api/best_model_trend?limit=20");
    renderBestTrend(data.rows || []);
  } catch (err) {
    bestTrendEl.innerHTML = `<p class=\"error\">加载轨迹失败: ${escapeHtml(err.message)}</p>`;
  }
}

function toCsv(rows) {
  if (!rows || rows.length === 0) return "";
  const cols = Object.keys(rows[0]);
  const esc = (v) => {
    const s = String(v ?? "");
    if (s.includes(",") || s.includes("\"") || s.includes("\n")) {
      return `"${s.replaceAll("\"", "\"\"")}"`;
    }
    return s;
  };
  const head = cols.join(",");
  const body = rows.map((r) => cols.map((c) => esc(r[c])).join(",")).join("\n");
  return `${head}\n${body}\n`;
}

function downloadText(filename, text, mime = "text/plain;charset=utf-8") {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function renderCompareSelectors() {
  const runs = state.runs || [];
  const opts = runs.map((r) => `<option value="${r.run_id}">${r.run_id}</option>`).join("");
  compareBaseRunEl.innerHTML = opts;
  compareTargetRunEl.innerHTML = opts;
  if (!compareBaseRunEl.value && runs[0]) compareBaseRunEl.value = runs[0].run_id;
  if (!compareTargetRunEl.value && runs[1]) compareTargetRunEl.value = runs[1].run_id;
}

function bestModel(rows) {
  if (!rows || rows.length === 0) return null;
  const sorted = [...rows].sort((a, b) => toNum(a.avg_MAE) - toNum(b.avg_MAE));
  return sorted[0];
}

async function compareRuns(baseRunId, targetRunId) {
  if (!baseRunId || !targetRunId) {
    compareResultEl.innerHTML = '<p class="empty">请选择两个 run。</p>';
    return;
  }
  if (baseRunId === targetRunId) {
    compareResultEl.innerHTML = '<p class="empty">请选择不同的两个 run。</p>';
    return;
  }

  try {
    const [baseBoard, targetBoard, baseSummary, targetSummary, baseMetrics, targetMetrics] = await Promise.all([
      fetchJson(`/api/leaderboard?run_id=${encodeURIComponent(baseRunId)}`),
      fetchJson(`/api/leaderboard?run_id=${encodeURIComponent(targetRunId)}`),
      fetchJson(`/api/run_summary?run_id=${encodeURIComponent(baseRunId)}`),
      fetchJson(`/api/run_summary?run_id=${encodeURIComponent(targetRunId)}`),
      fetchJson(`/api/metrics?run_id=${encodeURIComponent(baseRunId)}`),
      fetchJson(`/api/metrics?run_id=${encodeURIComponent(targetRunId)}`),
    ]);

    const b = bestModel(baseBoard.rows || []);
    const t = bestModel(targetBoard.rows || []);
    const baseMae = b ? toNum(b.avg_MAE) : NaN;
    const targetMae = t ? toNum(t.avg_MAE) : NaN;
    const delta = Number.isFinite(baseMae) && Number.isFinite(targetMae) ? targetMae - baseMae : NaN;

    const summaryRows = [
      {
        item: "best_model",
        base: b ? b.model_name : "-",
        target: t ? t.model_name : "-",
        delta: "-",
      },
      {
        item: "best_avg_MAE",
        base: Number.isFinite(baseMae) ? baseMae.toFixed(6) : "-",
        target: Number.isFinite(targetMae) ? targetMae.toFixed(6) : "-",
        delta: Number.isFinite(delta) ? delta.toFixed(6) : "-",
      },
      {
        item: "model_variants",
        base: String((baseSummary.summary?.models || []).length),
        target: String((targetSummary.summary?.models || []).length),
        delta: "-",
      },
      {
        item: "failed_models",
        base: String((baseSummary.summary?.failed_models || []).length),
        target: String((targetSummary.summary?.failed_models || []).length),
        delta: "-",
      },
    ];

    renderTable(compareResultEl, summaryRows, { key: "compare", limit: 20 });

    const baseSeg = aggregateBestBySegment(baseMetrics.rows || []);
    const targetSeg = aggregateBestBySegment(targetMetrics.rows || []);
    const baseMap = new Map(baseSeg.map((r) => [`${r.segment_key}|${r.segment_value}`, r]));
    const targetMap = new Map(targetSeg.map((r) => [`${r.segment_key}|${r.segment_value}`, r]));
    const keys = [...new Set([...baseMap.keys(), ...targetMap.keys()])].sort();
    const segRows = keys.map((k) => {
      const bRow = baseMap.get(k);
      const tRow = targetMap.get(k);
      const bMae = bRow ? toNum(bRow.best_MAE) : NaN;
      const tMae = tRow ? toNum(tRow.best_MAE) : NaN;
      return {
        segment: k,
        base_best_model: bRow ? bRow.best_model : "-",
        base_best_MAE: Number.isFinite(bMae) ? bMae.toFixed(6) : "-",
        target_best_model: tRow ? tRow.best_model : "-",
        target_best_MAE: Number.isFinite(tMae) ? tMae.toFixed(6) : "-",
        delta_target_minus_base: Number.isFinite(bMae) && Number.isFinite(tMae) ? (tMae - bMae).toFixed(6) : "-",
      };
    });
    renderTable(compareSegmentsEl, segRows, { key: "compare_segments", limit: 20 });
  } catch (err) {
    compareResultEl.innerHTML = `<p class="error">对比失败: ${escapeHtml(err.message)}</p>`;
    compareSegmentsEl.innerHTML = "";
  }
}

async function fetchJson(url, options = {}) {
  const resp = await fetch(url, options);
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.error || `Request failed: ${resp.status}`);
  }
  return data;
}

function renderRuns(runs) {
  runsEl.innerHTML = runs
    .map(
      (r) => `
        <div class="run-item ${currentRunId === r.run_id ? "active" : ""}" data-run-id="${r.run_id}">
          <div><strong>${r.run_id}</strong></div>
          <div>实验: ${r.experiment || "-"}</div>
          <div>数据版本: ${r.dataset_version || "-"}</div>
          <div>失败模型: ${r.failed_count ?? 0}</div>
          <button data-run-id="${r.run_id}">查看结果</button>
        </div>
      `
    )
    .join("");

  runsEl.querySelectorAll(".run-item").forEach((item) => {
    item.addEventListener("click", async (event) => {
      const runId = event.currentTarget.getAttribute("data-run-id");
      if (!runId) return;
      await loadRunResult(runId);
    });
  });

  runsEl.querySelectorAll(".run-item button").forEach((btn) => {
    btn.addEventListener("click", async (event) => {
      event.stopPropagation();
      const runId = btn.getAttribute("data-run-id");
      if (!runId) return;
      await loadRunResult(runId);
    });
  });
}

async function loadConfigs() {
  try {
    const data = await fetchJson("/api/configs");
    state.configs = data.configs || [];
    configSelectEl.innerHTML = state.configs.map((c) => `<option value="${c}">${c}</option>`).join("");
    const current = state.configs.includes(configInput.value.trim()) ? configInput.value.trim() : state.configs[0] || "";
    if (current) {
      configSelectEl.value = current;
      await loadConfigText(current);
    } else {
      configPreviewEl.textContent = "未发现配置文件。";
    }
  } catch (err) {
    configPreviewEl.textContent = `加载配置列表失败: ${err.message}`;
  }
}

async function loadConfigText(path) {
  if (!path) {
    configPreviewEl.textContent = "";
    return;
  }
  try {
    const data = await fetchJson(`/api/config_text?path=${encodeURIComponent(path)}`);
    configPreviewEl.textContent = data.text || "";
  } catch (err) {
    configPreviewEl.textContent = `加载配置内容失败: ${err.message}`;
  }
}

async function runWithConfig(configPath) {
  runBtn.disabled = true;
  setStatus("running", currentRunId || "-");
  setLog("正在运行实验，请稍候...");
  try {
    const payload = { config_path: configPath || configInput.value.trim() || "configs/experiments/model_zoo_smoke.yaml" };
    const submit = await fetchJson("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const taskId = submit.task_id;
    if (!taskId) {
      throw new Error("后端未返回 task_id");
    }
    const finalTask = await waitForTask(taskId);
    if (finalTask.status !== "succeeded") {
      const stderr = String(finalTask.stderr || finalTask.error || "").trim();
      throw new Error(stderr || "实验运行失败");
    }

    setLog((finalTask.stdout || "运行完成").trim() || "运行完成");
    currentRunId = null;
    await loadRuns();
    const outputDir = String(finalTask.output_dir || "");
    const runId = outputDir.split("/").filter(Boolean).pop();
    if (runId) {
      await loadRunResult(runId);
    }
  } catch (err) {
    setLog(`运行失败: ${err.message}`, true);
    setStatus("error", currentRunId || "-");
  } finally {
    runBtn.disabled = false;
  }
}

async function waitForTask(taskId, timeoutMs = 6 * 60 * 60 * 1000) {
  const startedAt = Date.now();
  while (true) {
    const task = await fetchJson(`/api/run_task?task_id=${encodeURIComponent(taskId)}`);
    if (task.status === "queued" || task.status === "running") {
      const tip = String(task.stdout || "").trim();
      setLog(tip || `任务 ${task.status === "queued" ? "排队中" : "运行中"}... task_id=${taskId}`);
      if (Date.now() - startedAt > timeoutMs) {
        throw new Error("等待任务超时");
      }
      await new Promise((resolve) => setTimeout(resolve, 1200));
      continue;
    }
    return task;
  }
}

async function loadRuns() {
  try {
    const data = await fetchJson("/api/runs");
    const runs = data.runs || [];
    state.runs = runs;
    if (runs.length === 0) {
      runsEl.innerHTML = "<p>还没有运行记录，先点击“运行实验”。</p>";
      leaderboardEl.innerHTML = '<p class="empty">暂无数据</p>';
      metricsEl.innerHTML = '<p class="empty">暂无数据</p>';
      leaderboardChartEl.innerHTML = '<p class="empty">暂无图表数据</p>';
      maeChartEl.innerHTML = '<p class="empty">暂无图表数据</p>';
      rmseChartEl.innerHTML = '<p class="empty">暂无图表数据</p>';
      runSummaryEl.innerHTML = '<p class="empty">暂无运行摘要。</p>';
      reportTextEl.textContent = "暂无报告。";
      artifactsEl.innerHTML = '<p class="empty">暂无产物。</p>';
      setStatus("idle");
      return;
    }

    renderRuns(runs);
    renderCompareSelectors();
    await loadBestTrend();
    if (!currentRunId) {
      await loadRunResult(runs[0].run_id);
    }
  } catch (err) {
    setLog(`加载运行记录失败: ${err.message}`, true);
    setStatus("error", currentRunId || "-");
  }
}

async function loadRunResult(runId) {
  try {
    currentRunId = runId;
    const [datasetProfileData, failedModelsData, leaderboardPayload, metricsPayload, stabilityPayload, summaryPayload, reportPayload, artifactsPayload] =
      await Promise.all([
        fetchJson(`/api/dataset_profile?run_id=${encodeURIComponent(runId)}`),
        fetchJson(`/api/failed_models?run_id=${encodeURIComponent(runId)}`),
        fetchJson(`/api/leaderboard?run_id=${encodeURIComponent(runId)}`),
        fetchJson(`/api/metrics?run_id=${encodeURIComponent(runId)}`),
        fetchJson(`/api/stability?run_id=${encodeURIComponent(runId)}`),
        fetchJson(`/api/run_summary?run_id=${encodeURIComponent(runId)}`),
        fetchJson(`/api/report?run_id=${encodeURIComponent(runId)}`),
        fetchJson(`/api/artifacts?run_id=${encodeURIComponent(runId)}`),
      ]);

    state.leaderboardRows = leaderboardPayload.rows || [];
    state.metricRows = metricsPayload.rows || [];
    state.stabilityRows = stabilityPayload.rows || [];
    state.lastSummary = summaryPayload.summary || {};
    state.lastReportText = reportPayload.report || "";

    updateSiteFilter();
    renderCurrentView();
    renderProfile(datasetProfileData.profile || {});
    renderFailedModels(failedModelsData.failed_models || []);
    renderRunSummary(summaryPayload.summary || {});
    renderReport(reportPayload.report || "");
    renderArtifacts(artifactsPayload.artifacts || []);

    renderRuns((await fetchJson("/api/runs")).runs || []);
    setStatus("ready", runId);
    setLog(`当前查看: ${runId}`);
  } catch (err) {
    setLog(`加载运行结果失败: ${err.message}`, true);
    setStatus("error", runId);
  }
}

pageTabsEl.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    const page = btn.getAttribute("data-page") || "arena";
    switchPage(page);
  });
});

siteFilterEl.addEventListener("change", () => {
  state.selectedSite = siteFilterEl.value;
  renderCurrentView();
});

leaderMetricEl.addEventListener("change", () => {
  state.leaderMetric = leaderMetricEl.value;
  renderCurrentView();
});

segmentFilterEl.addEventListener("change", () => {
  state.segmentFilter = segmentFilterEl.value;
  state.tableExpanded.metrics = false;
  renderCurrentView();
});

modelSearchEl.addEventListener("input", () => {
  state.modelSearch = modelSearchEl.value.trim();
  state.tableExpanded.leaderboard = false;
  state.tableExpanded.metrics = false;
  renderCurrentView();
});

toggleLogBtn.addEventListener("click", () => {
  const collapsed = logEl.classList.toggle("collapsed");
  toggleLogBtn.textContent = collapsed ? "展开日志" : "收起日志";
});

runBtn.addEventListener("click", async () => {
  await runWithConfig(configInput.value.trim());
});

refreshBtn.addEventListener("click", loadRuns);

reloadConfigsBtn.addEventListener("click", loadConfigs);

configSelectEl.addEventListener("change", async () => {
  const path = configSelectEl.value;
  await loadConfigText(path);
});

useConfigBtn.addEventListener("click", async () => {
  const path = configSelectEl.value;
  configInput.value = path;
  setLog(`已选择配置: ${path}`);
  switchPage("arena");
});

runSelectedConfigBtn.addEventListener("click", async () => {
  const path = configSelectEl.value;
  if (!path) return;
  configInput.value = path;
  switchPage("arena");
  await runWithConfig(path);
});

reloadReportBtn.addEventListener("click", async () => {
  if (!currentRunId) return;
  await loadRunResult(currentRunId);
  await loadBestTrend();
});

downloadReportBtn.addEventListener("click", () => {
  if (!currentRunId) return;
  downloadText(`${currentRunId}_report.md`, state.lastReportText || "");
});

downloadLeaderboardBtn.addEventListener("click", () => {
  if (!currentRunId) return;
  downloadText(`${currentRunId}_leaderboard.csv`, toCsv(state.leaderboardRows), "text/csv;charset=utf-8");
});

downloadMetricsBtn.addEventListener("click", () => {
  if (!currentRunId) return;
  downloadText(`${currentRunId}_metrics.csv`, toCsv(state.metricRows), "text/csv;charset=utf-8");
});

compareRunsBtn.addEventListener("click", async () => {
  await compareRuns(compareBaseRunEl.value, compareTargetRunEl.value);
});

reloadTrendBtn.addEventListener("click", loadBestTrend);

document.querySelectorAll(".quick").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const path = btn.getAttribute("data-config") || "";
    if (!path) return;
    configInput.value = path;
    if (configSelectEl.querySelector(`option[value="${path}"]`)) {
      configSelectEl.value = path;
      await loadConfigText(path);
    }
    setLog(`快速选择配置: ${path}`);
    switchPage("lab");
  });
});

async function bootstrap() {
  setStatus("idle");
  switchPage("arena");
  await Promise.all([loadConfigs(), loadRuns(), loadStorageSummary()]);
}

reloadStorageBtn.addEventListener("click", loadStorageSummary);
cleanupPreviewBtn.addEventListener("click", async () => {
  await runCleanup(true);
});
cleanupExecuteBtn.addEventListener("click", async () => {
  await runCleanup(false);
});

bootstrap();
