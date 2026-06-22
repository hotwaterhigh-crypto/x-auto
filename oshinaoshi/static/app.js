const api = (p, opt) => fetch(p, opt).then(r => r.json());
const $ = s => document.querySelector(s);
const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
const esc = s => (s ?? "").toString().replace(/[&<>]/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]));
const todayStr = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const fmtDateTime = s => { if (!s) return ""; const [d, t] = s.split(" "); const [, m, dd] = d.split("-"); return `${+m}/${+dd} ${(t || "").slice(0, 5)}`; };

let chart = null;
let chartMetric = "active_count";
let dashData = null;

const PRIO = { 1: { l: "高", c: "p-hi" }, 2: { l: "中", c: "p-mid" }, 3: { l: "低", c: "p-lo" } };
const prioBadge = p => `<span class="badge ${PRIO[p || 2].c}">優先${PRIO[p || 2].l}</span>`;
const prioSelect = (id, p) => `<select class="prio-sel" data-prio="${id}">
  <option value="1"${p == 1 ? " selected" : ""}>優先 高</option>
  <option value="2"${p == 2 ? " selected" : ""}>優先 中</option>
  <option value="3"${p == 3 ? " selected" : ""}>優先 低</option></select>`;
const moveSelect = (id, curCid) => {
  const opts = craftsmen.filter(c => c.id !== +curCid)
    .map(c => `<option value="${c.id}">${esc(c.name)}さんへ移動</option>`).join("");
  return `<select class="move-sel" data-job="${id}"><option value="">↪ 移動</option>${opts}</select>`;
};

// ---- タブ切替 ----
document.querySelectorAll(".tab").forEach(b => b.onclick = () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
  b.classList.add("active");
  document.querySelectorAll(".view").forEach(v => v.classList.add("hidden"));
  $("#view-" + b.dataset.view).classList.remove("hidden");
  if (b.dataset.view === "dashboard") loadDashboard();
  else if (b.dataset.view === "worker") loadWorker();
  else loadSettings();
});

// ===== ダッシュボード =====
async function loadDashboard() {
  dashData = await api("/api/dashboard");
  renderTotals(dashData);
  renderActivity();
  renderForecast(dashData);
  renderCraftsmanCards(dashData);
  renderChart(dashData);
  renderAlerts();
}

const WD = ["月", "火", "水", "木", "金", "土", "日"];

async function renderActivity() {
  const a = await api("/api/activity");
  $("#activity-date").textContent = "（" + fmtDate(a.date) + "）";
  const row = (j, kind) => `
    <div class="act-item">
      ${esc(j.item)} <span class="who">${esc(j.craftsman_name)}${j.customer_name ? " ・" + esc(j.customer_name) : ""}</span>
    </div>`;
  $("#act-new").innerHTML = a.new.length ? a.new.map(j => row(j)).join("") : `<div class="empty">なし</div>`;
  $("#act-done").innerHTML = a.done.length ? a.done.map(j => row(j)).join("") : `<div class="empty">なし</div>`;
}

function renderForecast(d) {
  const box = $("#forecast");
  if (!d.craftsmen.length) { box.innerHTML = `<div class="empty">職人が未登録です</div>`; return; }
  // バーの基準: 全職人で最も先まで埋まっている営業日数
  const maxDays = Math.max(7, ...d.craftsmen.map(c => c.forecast ? c.forecast.work_days : 0));
  box.innerHTML = "";
  d.craftsmen.forEach(c => {
    const f = c.forecast;
    const row = el("div", "fc link");
    row.onclick = (e) => { if (e.target.tagName !== "INPUT") location.href = "/c/" + c.id; };
    const nameHtml = `<span class="nm">${esc(c.name)}<span class="arrow">のページ ›</span></span>`;
    if (!f) {
      row.innerHTML = `<div class="top">${nameHtml}
        <span class="verdict">シフト未設定</span></div>
        <div class="meta">⚙️ シフト設定タブ、または職人ページで稼働時間を入れてください</div>`;
      box.appendChild(row); return;
    }
    let vclass = "free", verdict = "空き ✓";
    if (f.work_days >= 6) { vclass = "busy"; verdict = "ほぼ満杯"; }
    else if (f.work_days >= 3) { vclass = "mid"; verdict = "やや埋まり"; }
    const pct = Math.min(100, Math.round(f.work_days / maxDays * 100));
    const fill = f.finish_date && f.finish_date !== ">3年"
      ? `${fmtDate(f.finish_date)} まで埋まり` : (f.work_days ? "3年以上先まで" : "空き");
    row.innerHTML = `
      <div class="top">${nameHtml}
        <span class="verdict ${vclass}">${verdict}</span></div>
      <div class="bar"><i style="width:${pct}%"></i><span class="lbl">${fill}</span></div>
      <div class="meta">残り ${c.active_hours.toFixed(1)}h ・ 約 ${f.work_days} 営業日分
        ${f.free_from ? "・ 次に空くのは " + fmtDate(f.free_from) + "（" + WD[new Date(f.free_from).getDay() === 0 ? 6 : new Date(f.free_from).getDay() - 1] + "）" : ""}</div>`;
    box.appendChild(row);
  });
}

function renderTotals(d) {
  const t = d.totals;
  $("#totals").innerHTML = `
    <div class="total"><div class="n">${t.active_jobs}</div><div class="l">進行中の案件</div></div>
    <div class="total"><div class="n">${t.active_hours}</div><div class="l">残り工数(時間)</div></div>
    <div class="total ${t.due_soon ? "warn" : ""}"><div class="n">${t.due_soon}</div><div class="l">納期間近(2日内)</div></div>
    <div class="total ${t.overdue ? "danger" : ""}"><div class="n">${t.overdue}</div><div class="l">納期超過</div></div>`;
}

function renderCraftsmanCards(d) {
  const wrap = $("#craftsman-cards");
  wrap.innerHTML = "";
  if (!d.craftsmen.length) { wrap.innerHTML = `<div class="empty card">職人モードから職人を登録してください</div>`; return; }
  const maxH = Math.max(1, ...d.craftsmen.map(c => c.active_hours));
  d.craftsmen.forEach(c => {
    let pill = `<span class="pill calm">余裕</span>`;
    if (c.overdue_count) pill = `<span class="pill over">超過 ${c.overdue_count}</span>`;
    else if (c.due_soon_count) pill = `<span class="pill soon">間近 ${c.due_soon_count}</span>`;
    const card = el("div", "cm");
    card.innerHTML = `
      <div class="nm">${esc(c.name)} ${pill}</div>
      <div class="load"><i style="width:${Math.round(c.active_hours / maxH * 100)}%"></i></div>
      <dl>
        <dt>進行中</dt><dd>${c.active_count} 件</dd>
        <dt>残り工数</dt><dd>${c.active_hours.toFixed(1)} h</dd>
        <dt>直近納期</dt><dd>${c.nearest_due ? fmtDate(c.nearest_due) : "—"}</dd>
        <dt>完了済み</dt><dd>${c.done_count} 件</dd>
      </dl>`;
    wrap.appendChild(card);
  });
}

document.querySelectorAll(".seg").forEach(b => b.onclick = () => {
  document.querySelectorAll(".seg").forEach(x => x.classList.remove("active"));
  b.classList.add("active");
  chartMetric = b.dataset.metric;
  if (dashData) renderChart(dashData);
});

function renderChart(d) {
  const labels = d.craftsmen.map(c => c.name);
  const data = d.craftsmen.map(c => chartMetric === "active_hours" ? +c.active_hours.toFixed(1) : c.active_count);
  const colors = d.craftsmen.map(c => c.overdue_count ? "#c0492f" : c.due_soon_count ? "#d98324" : "#b5835a");
  if (chart) chart.destroy();
  chart = new Chart($("#chart"), {
    type: "bar",
    data: { labels, datasets: [{ data, backgroundColor: colors, borderRadius: 6 }] },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      maintainAspectRatio: false,
    },
  });
}

async function renderAlerts() {
  const jobs = await api("/api/jobs");
  const cmName = Object.fromEntries((dashData?.craftsmen || []).map(c => [c.id, c.name]));
  const today = dashData.today;
  const flagged = jobs
    .filter(j => j.status !== "完了" && j.due_date)
    .map(j => ({ ...j, late: j.due_date < today, soon: j.due_date >= today && daysBetween(today, j.due_date) <= 2 }))
    .filter(j => j.late || j.soon)
    .sort((a, b) => a.due_date.localeCompare(b.due_date));
  const box = $("#alerts");
  if (!flagged.length) { box.innerHTML = `<div class="empty">納期が近い案件はありません 👍</div>`; return; }
  box.innerHTML = "";
  flagged.forEach(j => {
    const row = el("div", "jobrow");
    row.innerHTML = `
      <div class="main">
        <div class="ttl">${esc(j.item)} <span class="sub">${esc(cmName[j.craftsman_id] || "未割当")}</span></div>
        <div class="sub">${esc(j.customer_name || "")} ・ 納期 ${fmtDate(j.due_date)}</div>
      </div>
      <span class="badge ${j.late ? "over" : "soon"}">${j.late ? "超過" : "あと" + daysBetween(today, j.due_date) + "日"}</span>`;
    box.appendChild(row);
  });
}

// ===== 職人モード =====
let craftsmen = [];

async function loadWorker() {
  craftsmen = await api("/api/craftsmen");
  const sel = $("#worker-select");
  const cur = sel.value;
  sel.innerHTML = craftsmen.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join("")
    + `<option value="__new">＋ 新しい職人を登録…</option>`;
  if (cur) sel.value = cur;
  const saved = localStorage.getItem("worker_id");
  if (saved && craftsmen.some(c => c.id == saved)) sel.value = saved;
  loadMyJobs();
}

async function addCraftsman() {
  const name = prompt("職人の名前を入力してください");
  if (!name || !name.trim()) return;
  const res = await api("/api/craftsmen", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
  if (res.error) { alert(res.error); return; }
  await loadWorker();
  if (res.id) {
    $("#worker-select").value = res.id;
    localStorage.setItem("worker_id", res.id);
  }
  loadMyJobs();
}

$("#add-worker").onclick = addCraftsman;

$("#worker-select").onchange = async (e) => {
  if (e.target.value === "__new") { await addCraftsman(); return; }
  localStorage.setItem("worker_id", $("#worker-select").value);
  loadMyJobs();
};

$("#job-form").onsubmit = async (e) => {
  e.preventDefault();
  const cid = $("#worker-select").value;
  if (!cid || cid === "__new") { alert("先に職人を選んでください"); return; }
  const fd = Object.fromEntries(new FormData(e.target));
  fd.craftsman_id = +cid;
  const res = await api("/api/jobs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(fd) });
  if (res.error) { alert(res.error); return; }
  e.target.reset();
  loadMyJobs();
};

async function loadMyJobs() {
  const cid = $("#worker-select").value;
  if (!cid || cid === "__new") { $("#my-jobs").innerHTML = `<div class="empty">職人を選択してください</div>`; return; }
  const jobs = await api("/api/jobs?craftsman_id=" + cid);
  const box = $("#my-jobs");
  if (!jobs.length) { box.innerHTML = `<div class="empty">まだ案件がありません</div>`; return; }
  box.innerHTML = "";
  const today = todayStr();
  jobs.forEach(j => {
    const late = j.status !== "完了" && j.due_date && j.due_date < today;
    const row = el("div", "jobrow");
    const next = j.status === "未着手" ? "作業中" : j.status === "作業中" ? "完了" : null;
    row.innerHTML = `
      <div class="main">
        <div class="ttl">${prioBadge(j.priority)} ${esc(j.garment ? j.garment + " " : "")}${esc(j.item)}
          <span class="badge s${j.status}">${j.status}</span>
          ${late ? `<span class="badge over">超過</span>` : ""}
          ${j.status === "完了" && j.completed_at ? `<span class="done-at">✓ ${fmtDateTime(j.completed_at)} 完了</span>` : ""}</div>
        <div class="sub">${j.store_name ? "🏠" + esc(j.store_name) + " " : ""}${j.gender ? esc(j.gender) + "・" : ""}${esc(j.customer_name || "")}${j.due_date ? " ・納期 " + fmtDate(j.due_date) : ""}${j.est_hours ? " ・" + j.est_hours + "h" : ""}</div>
      </div>
      <div class="statusbtns">
        ${prioSelect(j.id, j.priority)}
        ${moveSelect(j.id, cid)}
        ${next ? `<button class="mini" data-adv="${j.id}" data-to="${next}">${next}へ</button>` : ""}
        <button class="mini del" data-del="${j.id}">削除</button>
      </div>`;
    box.appendChild(row);
  });
  box.querySelectorAll(".prio-sel").forEach(s => s.onchange = async () => {
    await api("/api/jobs/" + s.dataset.prio, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ priority: +s.value }) });
    loadMyJobs();
  });
  box.querySelectorAll(".move-sel").forEach(s => s.onchange = async () => {
    const to = craftsmen.find(c => c.id === +s.value);
    if (!to) return;
    if (!confirm(`この案件を「${to.name}さん」に移動しますか？`)) { s.value = ""; return; }
    await api("/api/jobs/" + s.dataset.job, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ craftsman_id: to.id }) });
    loadMyJobs();
  });
  box.querySelectorAll("[data-adv]").forEach(b => b.onclick = async () => {
    await api("/api/jobs/" + b.dataset.adv, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: b.dataset.to }) });
    loadMyJobs();
  });
  box.querySelectorAll("[data-del]").forEach(b => b.onclick = async () => {
    if (!confirm("この案件を削除しますか？")) return;
    await api("/api/jobs/" + b.dataset.del, { method: "DELETE" });
    loadMyJobs();
  });
}

// ===== シフト設定 =====
const CAP_COLS = ["cap_mon", "cap_tue", "cap_wed", "cap_thu", "cap_fri", "cap_sat", "cap_sun"];

async function loadSettings() {
  const cms = await api("/api/craftsmen");
  const box = $("#shift-editor");
  if (!cms.length) { box.innerHTML = `<div class="empty">先に職人モードで職人を登録してください</div>`; return; }
  let html = `<table class="shift-table"><thead><tr><th>職人</th>`;
  WD.forEach((w, i) => html += `<th class="${i === 5 ? "sat" : i === 6 ? "sun" : ""}">${w}</th>`);
  html += `<th>週計</th></tr></thead><tbody>`;
  cms.forEach(c => {
    html += `<tr data-id="${c.id}"><td>${esc(c.name)} <span class="saved-flash">保存✓</span></td>`;
    CAP_COLS.forEach(col => html += `<td><input type="number" min="0" step="0.5" value="${c[col]}" data-col="${col}"></td>`);
    const wk = CAP_COLS.reduce((s, col) => s + (+c[col] || 0), 0);
    html += `<td class="wk">${wk}h</td></tr>`;
  });
  html += `</tbody></table>`;
  box.innerHTML = html;

  box.querySelectorAll("input").forEach(inp => inp.onchange = async () => {
    const tr = inp.closest("tr");
    const cid = tr.dataset.id;
    const payload = { [inp.dataset.col]: +inp.value || 0 };
    await api("/api/craftsmen/" + cid, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const wk = [...tr.querySelectorAll("input")].reduce((s, i) => s + (+i.value || 0), 0);
    tr.querySelector(".wk").textContent = wk + "h";
    const flash = tr.querySelector(".saved-flash");
    flash.classList.add("show");
    setTimeout(() => flash.classList.remove("show"), 1200);
  });
}

// ---- utils ----
function fmtDate(s) { const [y, m, d] = s.split("-"); return `${+m}/${+d}`; }
function daysBetween(a, b) { return Math.round((new Date(b) - new Date(a)) / 86400000); }

loadDashboard();
