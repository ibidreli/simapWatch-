const fmtInt = new Intl.NumberFormat("de-CH");
const fmtMoney = new Intl.NumberFormat("de-CH", { style: "currency", currency: "CHF", maximumFractionDigits: 0 });

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function metricCard(label, value) {
  const article = document.createElement("article");
  article.className = "metric";
  article.innerHTML = `<div class="metric-label">${label}</div><div class="metric-value">${value}</div>`;
  return article;
}

function renderSummary(summary) {
  const container = document.getElementById("summary-cards");
  container.innerHTML = "";
  container.append(
    metricCard("Zuschlagszeilen", fmtInt.format(summary.award_count)),
    metricCard("Gesamtvolumen", fmtMoney.format(summary.total_volume_chf)),
    metricCard("Gewinner", fmtInt.format(summary.winner_count)),
    metricCard("Auftraggeber", fmtInt.format(summary.buyer_count)),
    metricCard("Neue 30 Tage", fmtInt.format(summary.recent_30d_count)),
  );
}

function renderMonthly(series) {
  const container = document.getElementById("monthly-chart");
  container.innerHTML = "";
  const maxValue = Math.max(...series.map(item => item.total_volume_chf), 1);
  series.forEach(item => {
    const bar = document.createElement("div");
    bar.className = "bar";
    const percentage = Math.max((item.total_volume_chf / maxValue) * 100, item.total_volume_chf > 0 ? 6 : 0);
    bar.innerHTML = `
      <div class="bar-fill" style="height:${percentage}%"></div>
      <div class="bar-label">${item.month.slice(2)}</div>
      <div class="bar-value">${fmtInt.format(item.award_count)}</div>
    `;
    container.appendChild(bar);
  });
}

function renderRankList(targetId, items, nameKey, valueKey, formatter) {
  const container = document.getElementById(targetId);
  container.innerHTML = "";
  items.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "rank-item";
    row.innerHTML = `
      <div class="rank-index">${index + 1}</div>
      <div>
        <div class="rank-name">${item[nameKey]}</div>
        <div class="rank-meta">${valueKey === "award_count" ? "Zuschläge" : "Volumen"}</div>
      </div>
      <div class="rank-value">${formatter(item[valueKey])}</div>
    `;
    container.appendChild(row);
  });
}

function renderRecentAwards(rows) {
  const container = document.getElementById("recent-awards");
  container.innerHTML = "";
  rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.publication_date || ""}</td>
      <td>${row.publication_number || ""}</td>
      <td><a href="${row.project_url}" target="_blank" rel="noreferrer">${row.title || ""}</a></td>
      <td>${row.winner_name || ""}</td>
      <td>${row.procurement_office || ""}</td>
      <td>${fmtMoney.format(row.award_amount_chf || 0)}</td>
    `;
    container.appendChild(tr);
  });
}

function renderMap(flows) {
  const map = L.map("flow-map", {
    scrollWheelZoom: true,
    zoomControl: true,
  }).setView([46.82, 8.23], 8);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap-Mitwirkende",
    maxZoom: 18,
  }).addTo(map);

  const bounds = [];
  flows.forEach(flow => {
    const from = [flow.from.lat, flow.from.lon];
    const to = [flow.to.lat, flow.to.lon];
    bounds.push(from, to);

    const line = L.polyline([from, to], {
      color: "#d95d39",
      weight: 2,
      opacity: 0.42,
    }).addTo(map);

    const popupHtml = `
      <div class="flow-popup">
        <strong>${flow.title || ""}</strong><br>
        ${flow.procurement_office || ""} → ${flow.winner_name || ""}<br>
        ${fmtMoney.format(flow.award_amount_chf || 0)}
      </div>
    `;
    line.bindPopup(popupHtml);

    L.circleMarker(from, {
      radius: 5,
      color: "#264653",
      weight: 2,
      fillColor: "#fff",
      fillOpacity: 1,
    }).addTo(map);

    L.circleMarker(to, {
      radius: 5,
      color: "#2a9d8f",
      weight: 2,
      fillColor: "#fff",
      fillOpacity: 1,
    }).addTo(map);
  });

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [28, 28] });
  }
}

async function boot() {
  const response = await fetch("/api/dashboard");
  const payload = await response.json();
  setText("generated-at", payload.generated_at.replace("T", " ").replace("Z", " UTC"));
  renderSummary(payload.summary);
  renderMap(payload.map_flows || []);
  renderMonthly(payload.monthly_series);
  renderRankList("winner-list", payload.top_winners, "winner_name", "total_volume_chf", value => fmtMoney.format(value));
  renderRankList("buyer-list", payload.top_buyers, "procurement_office", "total_volume_chf", value => fmtMoney.format(value));
  renderRankList("cpv-list", payload.cpv_breakdown, "cpv_primary", "award_count", value => fmtInt.format(value));
  renderRecentAwards(payload.recent_awards);
}

boot().catch(error => {
  console.error(error);
  document.body.insertAdjacentHTML("beforeend", `<pre style="padding:20px;color:#b00020;">Dashboard konnte nicht geladen werden.</pre>`);
});
