// 案件の編集モーダル（職人モード・職人ページ共通）
(function () {
  const html = `
  <div id="job-editor" class="modal-overlay" hidden>
    <div class="modal">
      <h2>案件を編集</h2>
      <div class="row">
        <label class="field"><span>区分</span><select name="gender" class="js-gender"></select></label>
        <label class="field"><span>種類</span><select name="garment" class="js-garment"></select></label>
      </div>
      <label class="field"><span>直しの内容 <em>必須</em></span>
        <input name="item" list="item-menu-edit" autocomplete="off">
        <datalist class="js-item-menu" id="item-menu-edit"></datalist></label>
      <label class="field"><span>店舗名</span>
        <input name="store_name" list="store-menu-edit" autocomplete="off">
        <datalist class="js-store-list" id="store-menu-edit"></datalist></label>
      <label class="field"><span>お客様名</span><input name="customer_name" autocomplete="off"></label>
      <div class="row">
        <label class="field"><span>納期</span><input name="due_date" type="date"></label>
        <label class="field"><span>見積工数(時間) <em>後で可</em></span>
          <input name="est_hours" type="number" step="0.5" min="0" placeholder="未定なら空欄"></label>
      </div>
      <div class="row">
        <label class="field"><span>金額(円) <em>後で可</em></span>
          <input name="price" type="number" min="0" placeholder="未定なら空欄"></label>
        <label class="field"><span>優先度</span>
          <select name="priority">
            <option value="2">中（ふつう）</option>
            <option value="1">高（急ぎ）</option>
            <option value="3">低（後回し）</option>
          </select></label>
      </div>
      <label class="field"><span>状態</span>
        <select name="status"><option>未着手</option><option>作業中</option><option>完了</option></select></label>
      <label class="field"><span>メモ</span><input name="note" autocomplete="off"></label>
      <div class="modal-btns">
        <button type="button" class="mini je-cancel">キャンセル</button>
        <button type="button" class="primary je-save">保存する</button>
      </div>
    </div>
  </div>`;
  const tmp = document.createElement("div");
  tmp.innerHTML = html.trim();
  document.body.appendChild(tmp.firstElementChild);

  const overlay = document.getElementById("job-editor");
  const q = n => overlay.querySelector(`[name="${n}"]`);
  let currentId = null, savedCb = null;
  const FIELDS = ["gender", "garment", "item", "store_name", "customer_name",
    "due_date", "est_hours", "price", "priority", "status", "note"];

  function close() { overlay.hidden = true; }
  overlay.addEventListener("click", e => { if (e.target === overlay) close(); });
  overlay.querySelector(".je-cancel").onclick = close;
  overlay.querySelector(".je-save").onclick = async () => {
    if (!q("item").value.trim()) { alert("直しの内容を入力してください"); return; }
    const body = {};
    FIELDS.forEach(f => { body[f] = q(f).value; });
    const res = await fetch("/api/jobs/" + currentId, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(r => r.json());
    if (res.error) { alert(res.error); return; }
    close();
    if (savedCb) savedCb();
  };

  window.openJobEditor = function (job, onSaved) {
    if (window.fillJobOptions) window.fillJobOptions();
    currentId = job.id; savedCb = onSaved;
    ["gender", "garment", "item", "store_name", "customer_name", "due_date", "note"]
      .forEach(f => { q(f).value = job[f] || ""; });
    q("est_hours").value = job.est_hours || "";
    q("price").value = job.price || "";
    q("priority").value = job.priority || 2;
    q("status").value = job.status || "未着手";
    overlay.hidden = false;
  };
})();
