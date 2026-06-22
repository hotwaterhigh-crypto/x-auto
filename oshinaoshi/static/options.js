// 区分・品目の選択肢（お直し店で一般的なもの）
window.GENDERS = ["レディース", "メンズ", "兼用"];
window.GARMENTS = {
  "トップス・アウター": ["ジャケット", "スーツ（上着）", "コート", "ダウン・防寒着", "ブレザー",
    "シャツ・ブラウス", "ニット・セーター", "カットソー・Tシャツ", "カーディガン", "ベスト"],
  "ボトムス": ["パンツ・スラックス", "ジーンズ・デニム", "スカート", "スーツ（下）", "ハーフパンツ"],
  "ワンピース・セットアップ": ["ワンピース", "ドレス", "スーツ（上下セット）"],
  "和装・その他": ["着物・浴衣", "制服・ユニフォーム", "革・レザー製品", "バッグ・小物", "その他"],
};

// お直し内容（実店舗の修理メニューを参考にした定番リスト。手打ちも可）
window.ITEM_MENU = [
  // 裾・丈
  "裾上げ（シングル）", "裾上げ（ダブル）", "裾上げ（まつり縫い）", "裾上げ（三つ巻き）",
  "ジーンズ裾上げ（チェーンステッチ）", "股下詰め", "着丈詰め", "スカート丈詰め",
  "ワンピース丈詰め", "パンツにスリット作製",
  // ウエスト・幅
  "ウエスト詰め", "ウエスト出し", "ウエストゴム交換", "身幅詰め", "肩幅詰め",
  "裾幅詰め（テーパード）",
  // 袖
  "袖丈詰め", "袖丈出し", "袖口のお直し", "肩パッド取り外し",
  // ファスナー・ボタン
  "ファスナー交換", "ファスナー修理", "ボタン付け", "ボタン交換", "ボタンホール修理",
  "スナップ・ホック付け",
  // 修理・補修
  "破れ直し", "ほつれ直し", "穴かがり", "当て布補強",
  // リフォーム・その他
  "裏地交換", "サイズ直し（全体）", "リフォーム・リメイク", "ワッペン・ネーム縫い付け",
];

// 店舗名（選択式）
window.STORES = ["SARTO名駅", "ReSARTO栄", "GUCCI栄", "GUCCI松坂屋", "GUCCI高島屋"];

window.fillJobOptions = function () {
  document.querySelectorAll("datalist.js-store-list").forEach(dl => {
    dl.innerHTML = window.STORES.map(s => `<option value="${s}">`).join("");
  });
  document.querySelectorAll(".js-gender").forEach(sel => {
    sel.innerHTML = window.GENDERS.map(g => `<option value="${g}">${g}</option>`).join("");
  });
  document.querySelectorAll(".js-garment").forEach(sel => {
    let html = `<option value="">種類を選択…</option>`;
    for (const [group, items] of Object.entries(window.GARMENTS)) {
      html += `<optgroup label="${group}">` +
        items.map(it => `<option value="${it}">${it}</option>`).join("") + `</optgroup>`;
    }
    sel.innerHTML = html;
  });
  document.querySelectorAll("datalist.js-item-menu").forEach(dl => {
    dl.innerHTML = window.ITEM_MENU.map(it => `<option value="${it}">`).join("");
  });
};

// よくある日本人の名字（あいうえお行ごと）
window.SURNAMES = {
  "あ": ["阿部", "青木", "秋山", "浅野", "荒木", "新井", "石川", "石井", "井上", "伊藤",
    "今井", "上田", "内田", "宇野", "遠藤", "江口", "大野", "岡田", "小川", "奥村"],
  "か": ["加藤", "金子", "川村", "菊池", "北村", "木村", "工藤", "久保", "栗原", "小林",
    "近藤", "後藤", "河野", "小山"],
  "さ": ["佐藤", "斎藤", "坂本", "佐々木", "三枝", "塩田", "清水", "柴田", "鈴木", "杉山", "関", "園田"],
  "た": ["高橋", "田中", "竹内", "武田", "田村", "千葉", "塚本", "土屋", "寺田", "戸田", "富田"],
  "な": ["中村", "中島", "永井", "中野", "西村", "西田", "二宮", "野口", "野村", "野田"],
  "は": ["橋本", "長谷川", "浜田", "林", "原田", "樋口", "平田", "福田", "藤田", "古川", "星野", "堀"],
  "ま": ["前田", "松本", "増田", "松井", "三浦", "水野", "宮本", "村上", "村田", "森", "森田"],
  "や": ["安田", "山田", "山本", "山口", "山崎", "山下", "横山", "吉田", "吉川"],
  "ら": ["李", "頼", "良知"],
  "わ": ["渡辺", "渡部", "和田", "若林", "鷲尾"],
};

window.initNamePickers = function () {
  document.querySelectorAll(".name-picker").forEach(np => {
    const input = np.closest(".field").querySelector("input[name='customer_name']");
    const toggle = np.querySelector(".np-toggle");
    const panel = np.querySelector(".np-panel");
    const kanaBox = np.querySelector(".np-kana");
    const nameBox = np.querySelector(".np-names");
    if (toggle.dataset.ready) return;
    toggle.dataset.ready = "1";

    kanaBox.innerHTML = Object.keys(window.SURNAMES)
      .map(k => `<button type="button" class="np-k" data-k="${k}">${k}</button>`).join("");

    toggle.onclick = () => { panel.hidden = !panel.hidden; };
    kanaBox.querySelectorAll(".np-k").forEach(b => b.onclick = () => {
      kanaBox.querySelectorAll(".np-k").forEach(x => x.classList.remove("on"));
      b.classList.add("on");
      nameBox.innerHTML = window.SURNAMES[b.dataset.k]
        .map(n => `<button type="button" class="np-n" data-n="${n}">${n}</button>`).join("");
      nameBox.querySelectorAll(".np-n").forEach(nb => nb.onclick = () => {
        input.value = nb.dataset.n + "様";
        panel.hidden = true;
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
    });
  });
};

document.addEventListener("DOMContentLoaded", () => { window.fillJobOptions(); window.initNamePickers(); });
