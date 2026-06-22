const api = (p, opt) => fetch(p, opt).then(r => r.json());
const $ = s => document.querySelector(s);
const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
const esc = s => (s ?? "").toString().replace(/[&<>]/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]));
const WD = ["月", "火", "水", "木", "金", "土", "日"];
const fmtDate = s => { const [y, m, d] = s.split("-"); return `${+m}/${+d}`; };
const fmtDateTime = s => { if (!s) return ""; const [d, t] = s.split(" "); const [, m, dd] = d.split("-"); return `${+m}/${+dd} ${(t || "").slice(0, 5)}`; };
const daysBetween = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);
const todayStr = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const PRIO = { 1: { l: "高", c: "p-hi" }, 2: { l: "中", c: "p-mid" }, 3: { l: "低", c: "p-lo" } };
const prioBadge = p => `<span class="badge ${PRIO[p || 2].c}">優先${PRIO[p || 2].l}</span>`;
const prioSelect = (id, p) => `<select class="prio-sel" data-prio="${id}">
  <option value="1"${p == 1 ? " selected" : ""}>優先 高</option>
  <option value="2"${p == 2 ? " selected" : ""}>優先 中</option>
  <option value="3"${p == 3 ? " selected" : ""}>優先 低</option></select>`;

const CID = +location.pathname.split("/").pop();
let calYear, calMonth;        // シフトカレンダー用
let jcYear, jcMonth;          // 案件カレンダー用
let allCraftsmen = [];        // 移動先の選択肢
let allJobs = [];             // 案件カレンダー描画用

const moveSelect = (id) => {
  const opts = allCraftsmen.filter(c => c.id !== CID)
    .map(c => `<option value="${c.id}">${esc(c.name)}さんへ移動</option>`).join("");
  return `<select class="move-sel" data-job="${id}"><option value="">↪ 移動</option>${opts}</select>`;
};

// ===== 空き状況 + 案件 =====
async function loadDetail() {
  const d = await api(`/api/craftsmen/${CID}/detail`);
  if (d.error) { document.body.innerHTML = "<p style='padding:20px'>職人が見つかりません</p>"; return; }
  $("#title").textContent = "🧵 " + d.craftsman.name + " さん";
  document.title = d.craftsman.name + " — 職人ページ";
  allJobs = d.jobs;
  renderStatus(d);
  renderJobs(d.jobs, d.today);
  renderJobCalendar();
  loadSchedule();
}

async function loadSchedule() {
  const s = await api(`/api/craftsmen/${CID}/schedule`);
  const box = $("#schedule");
  if (s.no_shift) { box.innerHTML = `<div class="empty">シフト未設定です。下のカレンダーで稼働時間を入れると予定が出ます。</div>`; return; }
  if (!s.days.length) { box.innerHTML = `<div class="empty">割り当てる進行中の案件がありません 👍</div>`; return; }

  // 納期に間に合わない案件の警告
  const late = s.jobs.filter(j => j.late);
  let warn = "";
  if (late.length) {
    warn = `<div class="late-warn">⚠ 納期に間に合わない恐れ: ` +
      late.map(j => `${esc(j.item)}（納期 ${fmtDate(j.due)}${j.finish ? "→完了見込 " + fmtDate(j.finish) : ""}）`).join("、 ") + `</div>`;
  }

  let rows = s.days.map(day => {
    const items = day.items.map(it => {
      const lateThis = it.due && day.date > it.due;
      const pTag = it.priority !== 2 ? `<span class="badge ${PRIO[it.priority].c}">${PRIO[it.priority].l}</span> ` : "";
      return `<div class="sch-item${it.finishes ? " fin" : ""}">
        ${pTag}${esc(it.garment ? it.garment + " " : "")}${esc(it.item)}<span class="who">${it.customer ? " " + esc(it.customer) : ""}</span>
        <span class="h">${it.hours}h</span>
        ${it.finishes ? `<span class="tag done">完了</span>` : `<span class="tag cont">続き</span>`}
        ${lateThis ? `<span class="tag late">納期超</span>` : ""}
      </div>`;
    }).join("");
    const full = day.used >= day.capacity - 0.01;
    return `<tr>
      <td class="sch-date ${day.weekday === 5 ? "sat" : day.weekday === 6 ? "sun" : ""}">
        <div class="dd">${fmtDate(day.date)}</div><div class="ww">(${WD[day.weekday]})</div></td>
      <td class="sch-work">${items}</td>
      <td class="sch-cap ${full ? "full" : ""}">${day.used}<span class="slash">/${day.capacity}h</span></td>
    </tr>`;
  }).join("");

  box.innerHTML = warn + `<table class="sch-table">
    <thead><tr><th>日付</th><th>作業内容</th><th>時間</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function renderStatus(d) {
  const f = d.forecast;
  let line;
  if (!f) {
    line = `<div class="verdict">シフト未設定 — 下のカレンダーで稼働時間を入れてください</div>`;
  } else if (!f.finish_date) {
    line = `<div class="verdict free">いまは空きあり ✓ すぐ取りかかれます</div>`;
  } else if (f.finish_date === ">3年") {
    line = `<div class="verdict busy">3年以上先まで埋まっています</div>`;
  } else {
    let cls = f.work_days >= 6 ? "busy" : f.work_days >= 3 ? "mid" : "free";
    line = `<div class="verdict ${cls}">${fmtDate(f.finish_date)} まで埋まっています</div>
      <div class="meta" style="margin-top:6px">次に空くのは <strong>${fmtDate(f.free_from)}</strong>
      （${WD[(new Date(f.free_from).getDay() + 6) % 7]}）</div>`;
  }
  $("#status").innerHTML = `
    ${line}
    <dl class="status-dl">
      <dt>進行中</dt><dd>${d.active_count} 件</dd>
      <dt>残り工数</dt><dd>${d.active_hours.toFixed(1)} h</dd>
      <dt>納期超過</dt><dd>${d.overdue_count} 件</dd>
      <dt>完了済み</dt><dd>${d.done_count} 件</dd>
    </dl>`;
}

function renderJobs(jobs, today) {
  const box = $("#jobs");
  if (!jobs.length) { box.innerHTML = `<div class="empty">まだ案件がありません</div>`; return; }
  box.innerHTML = "";
  jobs.forEach(j => {
    const late = j.status !== "完了" && j.due_date && j.due_date < today;
    const next = j.status === "未着手" ? "作業中" : j.status === "作業中" ? "完了" : null;
    const row = el("div", "jobrow");
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
        ${moveSelect(j.id)}
        ${next ? `<button class="mini" data-adv="${j.id}" data-to="${next}">${next}へ</button>` : ""}
        <button class="mini del" data-del="${j.id}">削除</button>
      </div>`;
    box.appendChild(row);
  });
  box.querySelectorAll(".prio-sel").forEach(s => s.onchange = async () => {
    await api("/api/jobs/" + s.dataset.prio, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ priority: +s.value }) });
    reloadAll();
  });
  box.querySelectorAll(".move-sel").forEach(s => s.onchange = async () => {
    const to = allCraftsmen.find(c => c.id === +s.value);
    if (!to) return;
    if (!confirm(`この案件を「${to.name}さん」に移動しますか？`)) { s.value = ""; return; }
    await api("/api/jobs/" + s.dataset.job, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ craftsman_id: to.id }) });
    reloadAll();
  });
  box.querySelectorAll("[data-adv]").forEach(b => b.onclick = async () => {
    await api("/api/jobs/" + b.dataset.adv, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: b.dataset.to }) });
    reloadAll();
  });
  box.querySelectorAll("[data-del]").forEach(b => b.onclick = async () => {
    if (!confirm("この案件を削除しますか？")) return;
    await api("/api/jobs/" + b.dataset.del, { method: "DELETE" });
    reloadAll();
  });
}

$("#job-form").onsubmit = async (e) => {
  e.preventDefault();
  const fd = Object.fromEntries(new FormData(e.target));
  fd.craftsman_id = CID;
  const res = await api("/api/jobs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(fd) });
  if (res.error) { alert(res.error); return; }
  e.target.reset();
  reloadAll();
};

// ===== 案件カレンダー（納期ベース） =====
function renderJobCalendar() {
  const grid = $("#job-calendar");
  if (!grid) return;
  $("#jc-title").textContent = `${jcYear}年 ${jcMonth}月`;
  const first = new Date(jcYear, jcMonth - 1, 1);
  const firstWd = (first.getDay() + 6) % 7;       // 月=0
  const daysInMonth = new Date(jcYear, jcMonth, 0).getDate();
  const todayIso = todayStr();
  const pad = n => String(n).padStart(2, "0");

  // 納期(due_date)が当月の案件を日付ごとにまとめる
  const byDay = {};
  allJobs.forEach(j => {
    if (!j.due_date) return;
    const [y, m] = j.due_date.split("-").map(Number);
    if (y === jcYear && m === jcMonth) (byDay[+j.due_date.slice(8, 10)] ||= []).push(j);
  });

  grid.innerHTML = "";
  WD.forEach((w, i) => grid.appendChild(el("div", "cal-dow" + (i === 5 ? " sat" : i === 6 ? " sun" : ""), w)));
  for (let i = 0; i < firstWd; i++) grid.appendChild(el("div", "cal-cell empty-cell"));
  for (let day = 1; day <= daysInMonth; day++) {
    const iso = `${jcYear}-${pad(jcMonth)}-${pad(day)}`;
    const wd = (new Date(jcYear, jcMonth - 1, day).getDay() + 6) % 7;
    const cell = el("div", "cal-cell jc-cell" + (wd === 5 ? " sat" : wd === 6 ? " sun" : "") + (iso === todayIso ? " today" : ""));
    let html = `<span class="d">${day}</span>`;
    (byDay[day] || []).forEach(j => {
      const over = j.status !== "完了" && j.due_date < todayIso;
      const done = j.status === "完了";
      const label = esc((j.garment ? j.garment + " " : "") + j.item);
      html += `<div class="jc-job ${PRIO[j.priority || 2].c}${over ? " over" : ""}${done ? " done" : ""}"
        title="${esc(j.customer_name || "")} ${label}">${done ? "✓ " : ""}${label}</div>`;
    });
    cell.innerHTML = html;
    grid.appendChild(cell);
  }
  const now = new Date();
  const cur = now.getFullYear() * 12 + now.getMonth();
  const shown = jcYear * 12 + (jcMonth - 1);
  $("#jc-prev").disabled = shown <= cur - 24;   // 2年前まで遡れる
  $("#jc-next").disabled = shown >= cur + 35;   // 約3年先まで
}

$("#jc-prev").onclick = () => { if (--jcMonth < 1) { jcMonth = 12; jcYear--; } renderJobCalendar(); };
$("#jc-next").onclick = () => { if (++jcMonth > 12) { jcMonth = 1; jcYear++; } renderJobCalendar(); };

// ===== 月間カレンダー =====
async function loadCalendar() {
  const cal = await api(`/api/craftsmen/${CID}/calendar?year=${calYear}&month=${calMonth}`);
  $("#cal-title").textContent = `${cal.year}年 ${cal.month}月`;
  $("#cal-total").textContent = `この月の合計: ${cal.month_total}h`;
  const grid = $("#calendar");
  grid.innerHTML = "";
  WD.forEach((w, i) => grid.appendChild(el("div", "cal-dow" + (i === 5 ? " sat" : i === 6 ? " sun" : ""), w)));
  for (let i = 0; i < cal.first_weekday; i++) grid.appendChild(el("div", "cal-cell empty-cell"));
  const todayIso = todayStr();
  cal.days.forEach(day => {
    const cell = el("div", "cal-cell" + (day.is_override ? " override" : "") +
      (day.weekday === 5 ? " sat" : day.weekday === 6 ? " sun" : "") +
      (day.date === todayIso ? " today" : ""));
    cell.innerHTML = `<span class="d">${day.day}</span>`;
    const inp = el("input");
    inp.type = "number"; inp.min = "0"; inp.step = "0.5"; inp.value = day.hours;
    inp.onchange = async () => {
      await api(`/api/craftsmen/${CID}/shift`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ date: day.date, hours: inp.value }) });
      loadCalendar();   // 合計と色を更新
      loadDetail();     // 予測も更新
    };
    cell.appendChild(inp);
    grid.appendChild(cell);
  });
  // 月の移動可能範囲: 今月 〜 約3年先(35ヶ月先)
  const now = new Date();
  const cur = now.getFullYear() * 12 + now.getMonth();
  const shown = calYear * 12 + (calMonth - 1);
  $("#prev").disabled = shown <= cur;
  $("#next").disabled = shown >= cur + 35;
}

$("#prev").onclick = () => { if (--calMonth < 1) { calMonth = 12; calYear--; } loadCalendar(); };
$("#next").onclick = () => { if (++calMonth > 12) { calMonth = 1; calYear++; } loadCalendar(); };

$("#copy-week").onclick = async () => {
  if (!confirm(`${calYear}年${calMonth}月の1週目の時間を、同じ曜日の残りの日にコピーします。よろしいですか？\n（コピー後も各日は個別に直せます）`)) return;
  await api(`/api/craftsmen/${CID}/calendar/fill`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ year: calYear, month: calMonth }) });
  loadCalendar();
  loadDetail();
};

// ===== 折りたたみ =====
function initCollapse() {
  document.querySelectorAll(".card.collapsible").forEach(card => {
    const key = "oshi_collapse_" + card.dataset.key;
    const btn = card.querySelector(".collapse-btn");
    const apply = c => { card.classList.toggle("collapsed", c); btn.textContent = c ? "表示" : "隠す"; };
    apply(localStorage.getItem(key) === "1");
    btn.onclick = () => { const c = !card.classList.contains("collapsed"); apply(c); localStorage.setItem(key, c ? "1" : "0"); };
  });
}

function reloadAll() { loadDetail(); loadCalendar(); }

// init
const now = new Date();
calYear = now.getFullYear();
calMonth = now.getMonth() + 1;
jcYear = now.getFullYear();
jcMonth = now.getMonth() + 1;
initCollapse();
(async () => {
  allCraftsmen = await api("/api/craftsmen");   // 移動先リストを先に用意
  loadDetail();
  loadCalendar();
})();
