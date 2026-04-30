const fmtInt = new Intl.NumberFormat("de-CH");
const fmtMoney = new Intl.NumberFormat("de-CH", {
  style: "currency",
  currency: "CHF",
  maximumFractionDigits: 0,
});
const fmtDecimal = new Intl.NumberFormat("de-CH", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
});

const appState = {
  map: null,
  mapLayer: null,
  charts: {},
  options: null,
};

const palette = [
  "#0f6ab3",
  "#ef8f2f",
  "#178f6f",
  "#5c3d8d",
  "#d15a7b",
  "#3c9ca8",
  "#8a6f45",
  "#6b7280",
  "#2a9d8f",
  "#b4542a",
  "#356f44",
  "#7c4d89",
];

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) {
    node.textContent = value;
  }
}

function metricCard(label, value) {
  const article = document.createElement("article");
  article.className = "metric";
  article.innerHTML = `<div class="metric-label">${label}</div><div class="metric-value">${value}</div>`;
  return article;
}

function shortLabel(value, max = 30) {
  const text = String(value || "").trim();
  if (!text) return "-";
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}...`;
}

function formatMoneyAxis(value) {
  const amount = Number(value || 0);
  const abs = Math.abs(amount);
  if (abs >= 1_000_000_000) {
    return `${fmtDecimal.format(amount / 1_000_000_000)} Mrd.`;
  }
  if (abs >= 1_000_000) {
    return `${fmtDecimal.format(amount / 1_000_000)} Mio.`;
  }
  if (abs >= 1_000) {
    return `${fmtDecimal.format(amount / 1_000)} Tsd.`;
  }
  return fmtInt.format(Math.round(amount));
}

function formatMoneyCard(value) {
  const amount = Number(value || 0);
  const abs = Math.abs(amount);
  if (abs >= 1_000_000_000) {
    return `CHF\u00A0${fmtDecimal.format(amount / 1_000_000_000)}\u00A0Mrd.`;
  }
  if (abs >= 1_000_000) {
    return `CHF\u00A0${fmtDecimal.format(amount / 1_000_000)}\u00A0Mio.`;
  }
  return fmtMoney.format(amount).replace(/\s/g, "\u00A0");
}

function bucketLabel(bucket) {
  const mapping = {
    "<100k": "< 100k",
    "100k-500k": "100k-500k",
    "500k-1m": "500k-1M",
    "1m-5m": "1M-5M",
    "5m-20m": "5M-20M",
    ">20m": "> 20M",
    unknown: "Unbekannt",
    "1": "1 Angebot",
    "2": "2 Angebote",
    "3-5": "3-5",
    "6-10": "6-10",
    "11+": "11+",
  };
  return mapping[bucket] || bucket;
}

function setLoading(message = "") {
  setText("loading-indicator", message);
}

function renderSummary(summary) {
  const container = document.getElementById("summary-cards");
  container.innerHTML = "";

  container.append(
    metricCard("Zuschlagszeilen", fmtInt.format(summary.award_count || 0)),
    metricCard("Gesamtvolumen", formatMoneyCard(summary.total_volume_chf || 0)),
    metricCard("Durchschnitt", formatMoneyCard(summary.average_award_chf || 0)),
    metricCard("Median", formatMoneyCard(summary.median_award_chf || 0)),
    metricCard("Gewinner", fmtInt.format(summary.winner_count || 0)),
    metricCard("Neue 30 Tage", fmtInt.format(summary.recent_30d_count || 0)),
  );
}

function renderInsights(items) {
  const container = document.getElementById("insights-grid");
  if (!container) return;
  container.innerHTML = "";

  if (!items.length) {
    const article = document.createElement("article");
    article.className = "insight-card";
    article.innerHTML = '<div class="insight-label">Insights</div><div class="insight-value">-</div>';
    container.appendChild(article);
    return;
  }

  items.forEach(item => {
    const article = document.createElement("article");
    article.className = "insight-card";
    article.innerHTML = `
      <div class="insight-label">${item.title || "Insight"}</div>
      <div class="insight-value">${item.value || "-"}</div>
      <div class="insight-detail">${item.description || ""}</div>
    `;
    container.appendChild(article);
  });
}

function drawChart(key, config) {
  const canvas = document.getElementById(key);
  if (!canvas || typeof Chart === "undefined") {
    return;
  }

  if (appState.charts[key]) {
    appState.charts[key].destroy();
  }

  appState.charts[key] = new Chart(canvas.getContext("2d"), config);
}

function renderTrendChart(series, timeBucket = "month") {
  const labels = series.map(item => item.label || item.period_key || item.month || "-");
  const volumes = series.map(item => Math.round(item.total_volume_chf || 0));
  const counts = series.map(item => item.award_count || 0);
  const rangeLabel = {
    day: "Tag",
    week: "Woche",
    month: "Monat",
  }[timeBucket] || "Zeitraum";

  drawChart("monthly-volume-chart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          type: "bar",
          label: "Volumen (CHF)",
          data: volumes,
          backgroundColor: "rgba(15, 106, 179, 0.35)",
          borderColor: "rgba(15, 106, 179, 0.95)",
          borderWidth: 1,
          yAxisID: "y",
          borderRadius: 6,
        },
        {
          type: "line",
          label: `Anzahl Zuschläge (${rangeLabel})`,
          data: counts,
          yAxisID: "y1",
          borderColor: "rgba(239, 143, 47, 0.95)",
          backgroundColor: "rgba(239, 143, 47, 0.3)",
          pointRadius: 3,
          tension: 0.28,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            title: contexts => {
              const idx = contexts[0]?.dataIndex ?? 0;
              return series[idx]?.period_key || labels[idx];
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: value => formatMoneyAxis(value),
          },
        },
        y1: {
          beginAtZero: true,
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: {
            callback: value => fmtInt.format(value),
          },
        },
      },
    },
  });
}

function renderCpvChart(items) {
  const fullLabels = items.map(item => item.cpv_category || item.cpv_display || item.cpv_primary || "-");
  const labels = fullLabels.map(value => shortLabel(value, 44));
  const values = items.map(item => item.award_count || 0);

  drawChart("cpv-chart", {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: palette,
          borderWidth: 0,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: {
            boxWidth: 12,
          },
        },
        tooltip: {
          callbacks: {
            title: contexts => {
              const idx = contexts[0]?.dataIndex ?? 0;
              return fullLabels[idx] || labels[idx];
            },
            afterTitle: contexts => {
              const idx = contexts[0]?.dataIndex ?? 0;
              const codeCount = items[idx]?.code_count;
              if (!codeCount) return "";
              return `${codeCount} CPV-Codes gruppiert`;
            },
            label: context => {
              const idx = context.dataIndex ?? 0;
              const item = items[idx] || {};
              const count = item.award_count || 0;
              const share = item.share_of_awards_pct || 0;
              return `${fmtInt.format(count)} Zuschläge (${fmtDecimal.format(share)}%)`;
            },
            afterLabel: context => {
              const idx = context.dataIndex ?? 0;
              const preview = items[idx]?.codes_preview || [];
              if (!preview.length) return "";
              return `Codes: ${preview.join(", ")}${(items[idx]?.code_count || 0) > preview.length ? " ..." : ""}`;
            },
          },
        },
      },
    },
  });
}

function renderTopWinnersChart(items) {
  const labels = items.map(item => shortLabel(item.winner_name, 28));
  const values = items.map(item => Math.round(item.total_volume_chf || 0));

  drawChart("winners-chart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          axis: "y",
          data: values,
          backgroundColor: "rgba(23, 143, 111, 0.35)",
          borderColor: "rgba(23, 143, 111, 0.9)",
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: {
            callback: value => formatMoneyAxis(value),
          },
        },
      },
    },
  });
}

function renderProcurementTypeChart(items) {
  const labels = items.map(item => shortLabel(item.procurement_type, 26));
  const values = items.map(item => item.award_count || 0);

  drawChart("procurement-type-chart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: "rgba(239, 143, 47, 0.35)",
          borderColor: "rgba(239, 143, 47, 0.95)",
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { precision: 0 },
        },
      },
    },
  });
}

function renderWinnerCantonChart(items) {
  const filtered = items.filter(item => item.canton_code && item.canton_code !== "unknown");
  const labels = filtered.map(item => item.canton || item.canton_code || "-");
  const per100k = filtered.map(item => item.awards_per_100k || 0);
  const counts = filtered.map(item => item.award_count || 0);

  drawChart("winner-canton-chart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Zuschläge pro 100'000 Einwohner",
          data: per100k,
          backgroundColor: "rgba(15, 106, 179, 0.38)",
          borderColor: "rgba(15, 106, 179, 0.95)",
          borderWidth: 1,
          borderRadius: 6,
          yAxisID: "y",
        },
        {
          type: "line",
          label: "Absolute Zuschläge",
          data: counts,
          borderColor: "rgba(88, 76, 160, 0.95)",
          backgroundColor: "rgba(88, 76, 160, 0.25)",
          yAxisID: "y1",
          pointRadius: 3,
          tension: 0.25,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom" } },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: value => fmtDecimal.format(value),
          },
        },
        y1: {
          beginAtZero: true,
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: { precision: 0 },
        },
      },
    },
  });
}

function renderBuyerCantonChart(items) {
  const labels = items.map(item => item.canton || item.canton_code || "-");
  const volumes = items.map(item => Math.round(item.total_volume_chf || 0));

  drawChart("buyer-canton-chart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Volumen (CHF)",
          data: volumes,
          backgroundColor: "rgba(23, 143, 111, 0.36)",
          borderColor: "rgba(23, 143, 111, 0.95)",
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: value => formatMoneyAxis(value),
          },
        },
      },
    },
  });
}

function renderAwardSizeChart(items) {
  const filtered = items.filter(item => (item.award_count || 0) > 0);
  const labels = filtered.map(item => bucketLabel(item.bucket));
  const counts = filtered.map(item => item.award_count || 0);
  const volumeShare = filtered.map(item => item.share_of_volume_pct || 0);

  drawChart("award-size-chart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Zuschläge",
          data: counts,
          backgroundColor: "rgba(239, 143, 47, 0.38)",
          borderColor: "rgba(239, 143, 47, 0.95)",
          borderWidth: 1,
          borderRadius: 6,
          yAxisID: "y",
        },
        {
          type: "line",
          label: "Volumenanteil (%)",
          data: volumeShare,
          borderColor: "rgba(15, 106, 179, 0.95)",
          backgroundColor: "rgba(15, 106, 179, 0.2)",
          yAxisID: "y1",
          pointRadius: 3,
          tension: 0.28,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom" } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } },
        y1: {
          beginAtZero: true,
          position: "right",
          max: 100,
          grid: { drawOnChartArea: false },
          ticks: { callback: value => `${value}%` },
        },
      },
    },
  });
}

function renderCompetitionChart(items) {
  const filtered = items.filter(item => (item.award_count || 0) > 0);
  const labels = filtered.map(item => bucketLabel(item.offers_bucket));
  const counts = filtered.map(item => item.award_count || 0);

  drawChart("competition-chart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Zuschläge",
          data: counts,
          backgroundColor: "rgba(88, 76, 160, 0.35)",
          borderColor: "rgba(88, 76, 160, 0.95)",
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } },
      },
    },
  });
}

function renderCompetitionTypeChart(items) {
  const filtered = items.filter(item => (item.known_offers_award_count || 0) > 0);
  const labels = filtered.map(item => shortLabel(item.procurement_type, 24));
  const singleBidShare = filtered.map(item => item.single_bid_share_pct || 0);
  const avgOffers = filtered.map(item => item.average_offers_count ?? null);

  drawChart("competition-type-chart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Single-Bid Anteil (%)",
          data: singleBidShare,
          backgroundColor: "rgba(181, 68, 68, 0.34)",
          borderColor: "rgba(181, 68, 68, 0.95)",
          borderWidth: 1,
          borderRadius: 6,
          yAxisID: "y",
        },
        {
          type: "line",
          label: "Ø Angebote",
          data: avgOffers,
          borderColor: "rgba(15, 106, 179, 0.95)",
          backgroundColor: "rgba(15, 106, 179, 0.2)",
          yAxisID: "y1",
          pointRadius: 3,
          tension: 0.24,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom" } },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: { callback: value => `${value}%` },
        },
        y1: {
          beginAtZero: true,
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: { callback: value => fmtDecimal.format(value) },
        },
      },
    },
  });
}

function renderCantonFlowChart(items) {
  const labels = items.map(item => shortLabel(item.flow_label, 14));
  const counts = items.map(item => item.award_count || 0);

  drawChart("canton-flow-chart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          axis: "y",
          label: "Zuschläge",
          data: counts,
          backgroundColor: "rgba(60, 156, 168, 0.36)",
          borderColor: "rgba(60, 156, 168, 0.95)",
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, ticks: { precision: 0 } },
      },
    },
  });
}

function renderConcentrationChart(items) {
  const labels = items.map(item => `#${item.rank}`);
  const volumes = items.map(item => Math.round(item.winner_volume_chf || 0));
  const cumulative = items.map(item => item.cumulative_volume_share_pct || 0);

  drawChart("concentration-chart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Volumen je Gewinner (CHF)",
          data: volumes,
          backgroundColor: "rgba(21, 130, 88, 0.35)",
          borderColor: "rgba(21, 130, 88, 0.92)",
          borderWidth: 1,
          borderRadius: 6,
          yAxisID: "y",
        },
        {
          type: "line",
          label: "Kumulierte Volumenanteile (%)",
          data: cumulative,
          borderColor: "rgba(209, 90, 123, 0.95)",
          backgroundColor: "rgba(209, 90, 123, 0.2)",
          yAxisID: "y1",
          pointRadius: 2,
          tension: 0.2,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom" } },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: value => formatMoneyAxis(value),
          },
        },
        y1: {
          beginAtZero: true,
          position: "right",
          max: 100,
          grid: { drawOnChartArea: false },
          ticks: {
            callback: value => `${value}%`,
          },
        },
      },
    },
  });
}

function renderInterCantonTrendChart(items) {
  const labels = items.map(item => item.label || item.period_key || "-");
  const share = items.map(item => item.inter_canton_share_pct || 0);
  const knownCounts = items.map(item => item.known_canton_award_count || 0);

  drawChart("inter-canton-trend-chart", {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          type: "line",
          label: "Interkantonale Quote (%)",
          data: share,
          borderColor: "rgba(88, 76, 160, 0.95)",
          backgroundColor: "rgba(88, 76, 160, 0.2)",
          yAxisID: "y",
          pointRadius: 2,
          tension: 0.2,
        },
        {
          type: "bar",
          label: "Kanton-Fälle (n)",
          data: knownCounts,
          backgroundColor: "rgba(15, 106, 179, 0.28)",
          borderColor: "rgba(15, 106, 179, 0.8)",
          borderWidth: 1,
          yAxisID: "y1",
          borderRadius: 4,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom" } },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: { callback: value => `${value}%` },
        },
        y1: {
          beginAtZero: true,
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: { precision: 0 },
        },
      },
    },
  });
}

function renderRecentAwards(rows) {
  const container = document.getElementById("recent-awards");
  container.innerHTML = "";

  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="6">Keine Einträge für diese Filter.</td>';
    container.appendChild(tr);
    return;
  }

  rows.forEach(row => {
    const tr = document.createElement("tr");
    const title = row.title || "";
    const url = row.project_url || "#";
    tr.innerHTML = `
      <td>${row.publication_date || ""}</td>
      <td>${row.publication_number || ""}</td>
      <td><a href="${url}" target="_blank" rel="noreferrer">${title}</a></td>
      <td>${row.winner_name || ""}</td>
      <td>${row.procurement_office || ""}</td>
      <td>${fmtMoney.format(row.award_amount_chf || 0)}</td>
    `;
    container.appendChild(tr);
  });
}

function renderWinnerProfiles(rows) {
  const container = document.getElementById("winner-profiles");
  if (!container) return;
  container.innerHTML = "";

  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="6">Keine Profile verfügbar.</td>';
    container.appendChild(tr);
    return;
  }

  rows.slice(0, 16).forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.winner_name || ""}</td>
      <td>${row.winner_canton || "-"}</td>
      <td>${fmtInt.format(row.award_count || 0)}</td>
      <td>${row.average_offers_count == null ? "-" : fmtDecimal.format(row.average_offers_count)}</td>
      <td title="${row.primary_cpv_display || ""}">${shortLabel(row.primary_cpv_display || row.primary_cpv || "-", 44)}</td>
      <td>${row.share_of_volume_pct == null ? "-" : `${fmtDecimal.format(row.share_of_volume_pct)}%`}</td>
    `;
    container.appendChild(tr);
  });
}

function ensureMap() {
  if (appState.map) {
    return true;
  }

  if (typeof window.L === "undefined") {
    const mapNode = document.getElementById("flow-map");
    if (mapNode && !mapNode.dataset.leafletError) {
      mapNode.dataset.leafletError = "1";
      mapNode.textContent = "Karte konnte nicht geladen werden (Leaflet fehlt).";
    }
    console.warn("Leaflet library is not available; skipping map rendering.");
    return false;
  }

  appState.map = L.map("flow-map", {
    scrollWheelZoom: true,
    zoomControl: true,
  }).setView([46.82, 8.23], 8);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap-Mitwirkende",
    maxZoom: 18,
  }).addTo(appState.map);

  appState.mapLayer = L.layerGroup().addTo(appState.map);
  return true;
}

function renderMap(flows) {
  if (!ensureMap() || !appState.mapLayer) {
    return;
  }
  appState.mapLayer.clearLayers();

  const maxCount = Math.max(...flows.map(flow => flow.award_count || 1), 1);
  const maxVolume = Math.max(...flows.map(flow => flow.total_volume_chf || flow.award_amount_chf || 1), 1);
  const bounds = [];
  flows.forEach(flow => {
    if (!flow.from || !flow.to) return;
    const from = [flow.from.lat, flow.from.lon];
    const to = [flow.to.lat, flow.to.lon];
    bounds.push(from, to);
    const flowCount = flow.award_count || 1;
    const flowVolume = flow.total_volume_chf || flow.award_amount_chf || 0;
    const weightByCount = Math.sqrt(flowCount / maxCount);
    const weightByVolume = Math.sqrt(flowVolume / maxVolume);
    const weight = 1.4 + 5 * Math.max(weightByCount, weightByVolume);
    const interCanton = flow.intra_canton === false || (flow.from_canton && flow.to_canton && flow.from_canton !== flow.to_canton);
    const lineColor = interCanton ? "#ef8f2f" : "#0f6ab3";

    const line = L.polyline([from, to], {
      color: lineColor,
      weight,
      opacity: 0.58,
    }).addTo(appState.mapLayer);

    const popupTitle = flow.flow_label || `${flow.procurement_office || "-"} -> ${flow.winner_name || "-"}`;
    const popupCount = flow.award_count != null ? `${fmtInt.format(flow.award_count)} Zuschläge` : "";
    const popupVolume = fmtMoney.format(flow.total_volume_chf || flow.award_amount_chf || 0);
    const popupAvg = flow.average_award_chf ? fmtMoney.format(flow.average_award_chf) : null;
    const popupShare = flow.share_of_known_canton_volume_pct != null
      ? `${fmtDecimal.format(flow.share_of_known_canton_volume_pct)}% der bekannten Kanton-Volumen`
      : null;
    line.bindPopup(
      `<div class="flow-popup">
        <strong>${popupTitle}</strong><br>
        ${popupCount}<br>
        Volumen: ${popupVolume}${popupAvg ? `<br>Avg: ${popupAvg}` : ""}${popupShare ? `<br>${popupShare}` : ""}
      </div>`
    );

    L.circleMarker(from, {
      radius: Math.max(4, Math.min(10, 3 + weight)),
      color: "#0f6ab3",
      weight: 2,
      fillColor: "#fff",
      fillOpacity: 1,
    }).addTo(appState.mapLayer);

    L.circleMarker(to, {
      radius: Math.max(4, Math.min(10, 3 + weight)),
      color: "#178f6f",
      weight: 2,
      fillColor: "#fff",
      fillOpacity: 1,
    }).addTo(appState.mapLayer);
  });

  if (bounds.length > 0) {
    appState.map.fitBounds(bounds, { padding: [30, 30] });
  } else {
    appState.map.setView([46.82, 8.23], 8);
  }
}

function fillDatalist(targetId, values, displayKey = null) {
  const list = document.getElementById(targetId);
  if (!list) return;
  list.innerHTML = "";

  values.forEach(item => {
    const option = document.createElement("option");
    option.value = item.name;
    if (displayKey && item[displayKey]) {
      option.label = item[displayKey];
    }
    list.appendChild(option);
  });
}

function fillProcurementTypeSelect(values) {
  const select = document.getElementById("filter-procurement-type");
  if (!select) return;

  const current = select.value;
  select.innerHTML = '<option value="">Alle</option>';

  values.forEach(item => {
    const option = document.createElement("option");
    option.value = item.name;
    option.textContent = `${item.name} (${fmtInt.format(item.count)})`;
    select.appendChild(option);
  });

  select.value = current;
}

function initializeFiltersFromOptions(options) {
  fillDatalist("buyers-list", options.buyers || []);
  fillDatalist("winners-list", options.winners || []);
  fillDatalist("cpv-codes-list", options.cpv_codes || [], "display");
  fillProcurementTypeSelect(options.procurement_types || []);

  const from = document.getElementById("filter-from");
  const to = document.getElementById("filter-to");
  if (from && options.date_min) from.min = options.date_min;
  if (from && options.date_max) from.max = options.date_max;
  if (to && options.date_min) to.min = options.date_min;
  if (to && options.date_max) to.max = options.date_max;
}

function currentFormFilters() {
  const form = document.getElementById("filter-form");
  const formData = new FormData(form);
  const filters = {};

  for (const [key, value] of formData.entries()) {
    const text = String(value || "").trim();
    if (!text) continue;
    filters[key] = text;
  }

  return filters;
}

function toDashboardUrl(filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });

  params.set("top_n", "12");
  params.set("recent_limit", "20");
  params.set("map_limit", "260");
  params.set("months", "12");
  return `/api/dashboard?${params.toString()}`;
}

async function loadDashboard() {
  setLoading("Lade Dashboard...");
  const filters = currentFormFilters();

  try {
    const response = await fetch(toDashboardUrl(filters));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    const generatedAt = String(payload.generated_at || "").replace("T", " ").replace("Z", " UTC");

    setText("generated-at", generatedAt);
    setText("result-count", fmtInt.format(payload.meta?.filtered_award_count || 0));
    setText(
      "result-subline",
      `von ${fmtInt.format(payload.meta?.source_award_count || 0)} gesamt`
    );

    const timeSeries = payload.time_series || payload.monthly_series || [];
    const timeBucket = payload.meta?.time_bucket || "month";

    renderSummary(payload.summary || {});
    renderInsights(payload.insights || []);
    renderTrendChart(timeSeries, timeBucket);
    renderCpvChart(payload.cpv_category_breakdown || payload.cpv_breakdown || []);
    renderTopWinnersChart(payload.top_winners || []);
    renderProcurementTypeChart(payload.top_procurement_types || []);
    renderWinnerCantonChart(payload.winner_canton_breakdown || []);
    renderBuyerCantonChart(payload.buyer_canton_breakdown || []);
    renderAwardSizeChart(payload.award_size_breakdown || []);
    renderCompetitionChart(payload.competition_breakdown || []);
    renderCompetitionTypeChart(payload.competition_by_procurement_type || []);
    renderCantonFlowChart(payload.canton_flow_breakdown || []);
    renderConcentrationChart(payload.winner_concentration_curve || []);
    renderInterCantonTrendChart(payload.inter_canton_trend || []);
    renderWinnerProfiles(payload.winner_profiles || []);
    const mapFlows = (payload.map_flows_aggregated || []).length > 0
      ? payload.map_flows_aggregated
      : (payload.map_flows || []);
    renderMap(mapFlows);
    renderRecentAwards(payload.recent_awards || []);

    setLoading("");
  } catch (error) {
    console.error(error);
    setLoading("Fehler beim Laden.");
    document.body.insertAdjacentHTML(
      "beforeend",
      '<pre class="error" style="padding:16px;">Dashboard konnte nicht geladen werden.</pre>'
    );
  }
}

function applyRelativeRange(days) {
  const toInput = document.getElementById("filter-to");
  const fromInput = document.getElementById("filter-from");
  const now = new Date();
  const from = new Date(now);
  from.setDate(from.getDate() - days);

  const toIso = now.toISOString().slice(0, 10);
  const fromIso = from.toISOString().slice(0, 10);

  toInput.value = toIso;
  fromInput.value = fromIso;
}

function wireFilterEvents() {
  const form = document.getElementById("filter-form");
  const resetButton = document.getElementById("reset-filters");

  form.addEventListener("submit", event => {
    event.preventDefault();
    loadDashboard();
  });

  let debounceTimer = null;
  form.addEventListener("input", event => {
    const target = event.target;
    const isTextual = target && target.name === "text";
    const delay = isTextual ? 500 : 280;

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      loadDashboard();
    }, delay);
  });

  resetButton.addEventListener("click", () => {
    form.reset();
    loadDashboard();
  });

  document.querySelectorAll("[data-days]").forEach(button => {
    button.addEventListener("click", () => {
      const days = Number(button.getAttribute("data-days"));
      if (Number.isFinite(days) && days > 0) {
        applyRelativeRange(days);
        loadDashboard();
      }
    });
  });
}

async function boot() {
  wireFilterEvents();

  setLoading("Lade Filteroptionen...");
  const optionsResponse = await fetch("/api/dashboard/options?limit=320");
  if (!optionsResponse.ok) {
    throw new Error(`HTTP ${optionsResponse.status}`);
  }

  appState.options = await optionsResponse.json();
  initializeFiltersFromOptions(appState.options);

  setLoading("");
  await loadDashboard();
}

boot().catch(error => {
  console.error(error);
  setLoading("Fehler beim Start.");
  document.body.insertAdjacentHTML(
    "beforeend",
    '<pre class="error" style="padding:16px;">Dashboard konnte nicht initialisiert werden.</pre>'
  );
});
