"""お直し職人 仕事量管理 — データベース層 (SQLite, 標準ライブラリのみ)"""
import sqlite3
import os
import shutil
from datetime import date, datetime, timedelta

# データ保存先。クラウドでは永続ディスク(例: /var/data)を DATA_DIR で指定する。
DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(DATA_DIR, "data.db")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

STATUSES = ["未着手", "作業中", "完了"]

# 曜日ごとの稼働時間カラム (月=mon … 日=sun)
CAP_COLS = ["cap_mon", "cap_tue", "cap_wed", "cap_thu", "cap_fri", "cap_sat", "cap_sun"]
DEFAULT_CAPS = [6, 6, 6, 6, 6, 0, 0]  # 平日6h・土日休みを初期値に


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_conn()
    conn.execute("PRAGMA journal_mode=WAL")   # 複数アクセスに強く
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS craftsmen (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            active     INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            craftsman_id  INTEGER REFERENCES craftsmen(id) ON DELETE SET NULL,
            customer_name TEXT,
            item          TEXT NOT NULL,           -- 品目・内容 (例: スカート裾上げ)
            order_date    TEXT,                    -- 受注日 YYYY-MM-DD
            due_date      TEXT,                    -- 納期   YYYY-MM-DD
            est_hours     REAL NOT NULL DEFAULT 0, -- 見積工数(時間)
            price         INTEGER NOT NULL DEFAULT 0,
            status        TEXT NOT NULL DEFAULT '未着手',
            note          TEXT,
            created_at    TEXT NOT NULL,
            completed_at  TEXT
        );

        -- 日付ごとのシフト(稼働時間)。曜日パターンを上書きする。
        CREATE TABLE IF NOT EXISTS shifts (
            craftsman_id INTEGER NOT NULL REFERENCES craftsmen(id) ON DELETE CASCADE,
            date         TEXT NOT NULL,   -- YYYY-MM-DD
            hours        REAL NOT NULL,
            PRIMARY KEY (craftsman_id, date)
        );
        """
    )
    # --- マイグレーション: シフト(曜日別稼働時間)カラムを追加 ---
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(craftsmen)")}
    for col, default in zip(CAP_COLS, DEFAULT_CAPS):
        if col not in existing:
            conn.execute(f"ALTER TABLE craftsmen ADD COLUMN {col} REAL NOT NULL DEFAULT {default}")
    # --- マイグレーション: 案件の優先度 (1=高, 2=中, 3=低) ---
    job_cols = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}
    if "priority" not in job_cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 2")
    # --- マイグレーション: 区分(メンズ/レディース)と品目の種類 ---
    if "gender" not in job_cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN gender TEXT DEFAULT ''")
    if "garment" not in job_cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN garment TEXT DEFAULT ''")
    if "store_name" not in job_cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN store_name TEXT DEFAULT ''")
    conn.commit()
    conn.close()


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def backup_db(keep=90):
    """起動時にDBを backups/data-YYYY-MM-DD.db へコピー。直近 keep 日分を保持。
    3年間の継続運用に備え、ファイル破損や誤削除からデータを守る。"""
    if not os.path.exists(DB_PATH):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = os.path.join(BACKUP_DIR, f"data-{date.today().isoformat()}.db")
    if not os.path.exists(dest):
        try:
            shutil.copy2(DB_PATH, dest)
        except OSError:
            return
    files = sorted(f for f in os.listdir(BACKUP_DIR)
                   if f.startswith("data-") and f.endswith(".db"))
    for f in files[:-keep]:
        try:
            os.remove(os.path.join(BACKUP_DIR, f))
        except OSError:
            pass


# ---- 職人 ----
def list_craftsmen(include_inactive=False):
    conn = get_conn()
    q = "SELECT * FROM craftsmen"
    if not include_inactive:
        q += " WHERE active = 1"
    q += " ORDER BY id"
    rows = [dict(r) for r in conn.execute(q).fetchall()]
    conn.close()
    return rows


def get_craftsman(cid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM craftsmen WHERE id = ?", (cid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_craftsman(name):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO craftsmen (name, created_at) VALUES (?, ?)",
        (name.strip(), now_iso()),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def set_craftsman_active(cid, active):
    conn = get_conn()
    conn.execute("UPDATE craftsmen SET active = ? WHERE id = ?", (1 if active else 0, cid))
    conn.commit()
    conn.close()


def update_capacity(cid, caps):
    """caps = {'cap_mon': 6, ...} のうち渡されたものだけ更新。"""
    conn = get_conn()
    sets, params = [], []
    for col in CAP_COLS:
        if col in caps:
            sets.append(f"{col} = ?")
            params.append(float(caps[col] or 0))
    if sets:
        params.append(cid)
        conn.execute(f"UPDATE craftsmen SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
    conn.close()


def get_overrides(cid, from_date=None):
    """職人の日付別シフト上書きを {date: hours} で返す。from_date 以降のみ。"""
    conn = get_conn()
    q = "SELECT date, hours FROM shifts WHERE craftsman_id = ?"
    params = [cid]
    if from_date:
        q += " AND date >= ?"
        params.append(from_date)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return {r["date"]: r["hours"] for r in rows}


def set_shift(cid, day, hours):
    """指定日の稼働時間を設定(上書き)。"""
    conn = get_conn()
    conn.execute(
        """INSERT INTO shifts (craftsman_id, date, hours) VALUES (?,?,?)
           ON CONFLICT(craftsman_id, date) DO UPDATE SET hours = excluded.hours""",
        (cid, day, float(hours or 0)),
    )
    conn.commit()
    conn.close()


def clear_shift(cid, day):
    """上書きを消して曜日パターンに戻す。"""
    conn = get_conn()
    conn.execute("DELETE FROM shifts WHERE craftsman_id = ? AND date = ?", (cid, day))
    conn.commit()
    conn.close()


def month_calendar(cid, year, month):
    """その月の各日について、実効稼働時間と上書きかどうかを返す。"""
    c = get_craftsman(cid)
    if not c:
        return None
    caps = [c[col] for col in CAP_COLS]
    overrides = get_overrides(cid)
    first = date(year, month, 1)
    next_month = date(year + (month // 12), (month % 12) + 1, 1)
    days = []
    d = first
    while d < next_month:
        iso = d.isoformat()
        ov = iso in overrides
        hours = overrides[iso] if ov else caps[d.weekday()]
        days.append({
            "date": iso, "day": d.day, "weekday": d.weekday(),
            "hours": round(hours, 1), "is_override": ov,
        })
        d += timedelta(days=1)
    return {
        "year": year, "month": month, "craftsman": c,
        "first_weekday": first.weekday(),  # 月=0
        "days": days,
        "month_total": round(sum(x["hours"] for x in days), 1),
    }


def fill_month_from_week1(cid, year, month):
    """その月の「最初に出てくる各曜日(=1週目)」の時間を、同じ曜日の残り全日にコピーする。
    週パターン(曜日デフォルト)と同じ値の日は上書きを残さない(=色を付けない)。"""
    cal = month_calendar(cid, year, month)
    if not cal:
        return None
    weekly = [cal["craftsman"][col] for col in CAP_COLS]
    template = {}
    for d in cal["days"]:
        template.setdefault(d["weekday"], d["hours"])  # 各曜日の初出 = 1週目
    for d in cal["days"]:
        target = template[d["weekday"]]
        if abs(target - weekly[d["weekday"]]) < 1e-9:
            clear_shift(cid, d["date"])      # デフォルトと同じ → 上書き不要
        else:
            set_shift(cid, d["date"], target)
    return month_calendar(cid, year, month)


def _forecast(remaining_hours, caps, overrides=None):
    """残り工数を稼働時間で消化しきる日付を予測する。
    caps: [mon..sun] の曜日別稼働時間。overrides: {date: hours} の日付別上書き。
    返り値: {finish_date, work_days, free_from, weekly_hours} / シフト未設定なら None。"""
    overrides = overrides or {}
    weekly = sum(caps)
    if weekly <= 0 and not overrides:
        return None

    def hours_on(day):
        return overrides.get(day.isoformat(), caps[day.weekday()])

    today = date.today()
    if remaining_hours <= 0:
        return {"finish_date": None, "work_days": 0,
                "free_from": today.isoformat(), "weekly_hours": round(weekly, 1)}
    acc = 0.0
    work_days = 0
    finish = None
    for d in range(0, 1100):   # 約3年先まで予測
        day = today + timedelta(days=d)
        cap = hours_on(day)
        if cap > 0:
            acc += cap
            work_days += 1
            if acc >= remaining_hours:
                finish = day
                break
    if finish is None:  # 3年でも消化しきれない
        return {"finish_date": ">3年", "work_days": work_days,
                "free_from": None, "weekly_hours": round(weekly, 1)}
    # 次に空く日 = finish の翌稼働日
    free_from = finish + timedelta(days=1)
    for _ in range(0, 60):
        if hours_on(free_from) > 0:
            break
        free_from += timedelta(days=1)
    return {"finish_date": finish.isoformat(), "work_days": work_days,
            "free_from": free_from.isoformat(), "weekly_hours": round(weekly, 1)}


# ---- 案件 ----
JOB_FIELDS = ["craftsman_id", "customer_name", "item", "order_date",
              "due_date", "est_hours", "price", "status", "note", "priority",
              "gender", "garment", "store_name"]


def list_jobs(craftsman_id=None, status=None):
    conn = get_conn()
    q = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if craftsman_id is not None:
        q += " AND craftsman_id = ?"
        params.append(craftsman_id)
    if status is not None:
        q += " AND status = ?"
        params.append(status)
    q += " ORDER BY priority, (due_date IS NULL), due_date, id"
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return rows


def add_job(data):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO jobs
           (craftsman_id, customer_name, item, order_date, due_date,
            est_hours, price, status, note, priority, gender, garment, store_name, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data.get("craftsman_id"),
            (data.get("customer_name") or "").strip(),
            (data.get("item") or "").strip(),
            data.get("order_date") or None,
            data.get("due_date") or None,
            float(data.get("est_hours") or 0),
            int(data.get("price") or 0),
            data.get("status") or "未着手",
            (data.get("note") or "").strip(),
            int(data.get("priority") or 2),
            (data.get("gender") or "").strip(),
            (data.get("garment") or "").strip(),
            (data.get("store_name") or "").strip(),
            now_iso(),
        ),
    )
    conn.commit()
    jid = cur.lastrowid
    conn.close()
    return jid


def update_job(jid, data):
    conn = get_conn()
    sets, params = [], []
    for f in JOB_FIELDS:
        if f in data:
            sets.append(f"{f} = ?")
            val = data[f]
            if f == "est_hours":
                val = float(val or 0)
            elif f in ("price", "priority"):
                val = int(val or (2 if f == "priority" else 0))
            params.append(val)
    # 完了になったら completed_at を打つ / 戻したら消す
    if data.get("status") == "完了":
        sets.append("completed_at = ?")
        params.append(now_iso())
    elif "status" in data and data["status"] != "完了":
        sets.append("completed_at = NULL")
    if sets:
        params.append(jid)
        conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
    conn.close()


def delete_job(jid):
    conn = get_conn()
    conn.execute("DELETE FROM jobs WHERE id = ?", (jid,))
    conn.commit()
    conn.close()


# ---- 集計 (ダッシュボード) ----
def dashboard():
    """職人ごとの仕事量サマリを返す。"""
    today = date.today().isoformat()
    craftsmen = list_craftsmen()
    jobs = list_jobs()
    by_c = {c["id"]: {
        "id": c["id"], "name": c["name"],
        "active_count": 0, "active_hours": 0.0,
        "overdue_count": 0, "due_soon_count": 0,
        "nearest_due": None, "done_count": 0,
        "active_price": 0,
        "caps": [c[col] for col in CAP_COLS],
    } for c in craftsmen}

    for j in jobs:
        c = by_c.get(j["craftsman_id"])
        if not c:
            continue
        if j["status"] == "完了":
            c["done_count"] += 1
            continue
        c["active_count"] += 1
        c["active_hours"] += j["est_hours"] or 0
        c["active_price"] += j["price"] or 0
        due = j["due_date"]
        if due:
            if due < today:
                c["overdue_count"] += 1
            elif (datetime.fromisoformat(due) - datetime.fromisoformat(today)).days <= 2:
                c["due_soon_count"] += 1
            if c["nearest_due"] is None or due < c["nearest_due"]:
                c["nearest_due"] = due

    summary = list(by_c.values())
    for c in summary:
        c["active_hours"] = round(c["active_hours"], 1)
        c["forecast"] = _forecast(c["active_hours"], c["caps"], get_overrides(c["id"], today))
    totals = {
        "craftsmen": len(craftsmen),
        "active_jobs": sum(c["active_count"] for c in summary),
        "active_hours": round(sum(c["active_hours"] for c in summary), 1),
        "overdue": sum(c["overdue_count"] for c in summary),
        "due_soon": sum(c["due_soon_count"] for c in summary),
    }
    return {"today": today, "totals": totals, "craftsmen": summary}


def daily_schedule(cid, max_days=400):
    """進行中の案件を、納期の早い順にシフト(各日の稼働時間)へ日割りする。
    返り値: 日ごとの作業内容テーブル + 案件ごとの完了予定/納期遅れ判定。"""
    c = get_craftsman(cid)
    if not c:
        return None
    caps = [c[col] for col in CAP_COLS]
    overrides = get_overrides(cid)
    today = date.today()

    def hours_on(day):
        return overrides.get(day.isoformat(), caps[day.weekday()])

    if sum(caps) <= 0 and not overrides:
        return {"craftsman": c, "today": today.isoformat(), "days": [], "jobs": [], "no_shift": True}

    jobs = [j for j in list_jobs(craftsman_id=cid) if j["status"] != "完了"]
    jobs.sort(key=lambda j: (j["priority"], j["due_date"] is None, j["due_date"] or "", j["id"]))
    queue = [{"item": j["item"], "customer": j["customer_name"], "due": j["due_date"],
              "status": j["status"], "rem": float(j["est_hours"] or 0),
              "priority": j["priority"], "garment": j["garment"], "gender": j["gender"],
              "finish": None} for j in jobs]

    days = []
    qi = 0
    d = today
    guard = 0
    while qi < len(queue) and guard < max_days:
        cap = hours_on(d)
        if cap > 0:
            used = 0.0
            items = []
            while qi < len(queue) and used < cap - 1e-9:
                job = queue[qi]
                if job["rem"] <= 1e-9:  # 工数ゼロの案件 → その日の小タスク扱い
                    items.append({"item": job["item"], "customer": job["customer"],
                                  "due": job["due"], "hours": 0, "finishes": True,
                                  "priority": job["priority"], "garment": job["garment"]})
                    job["finish"] = d.isoformat()
                    qi += 1
                    continue
                alloc = min(job["rem"], cap - used)
                job["rem"] -= alloc
                used += alloc
                finishes = job["rem"] <= 1e-9
                items.append({"item": job["item"], "customer": job["customer"],
                              "due": job["due"], "hours": round(alloc, 1), "finishes": finishes,
                              "priority": job["priority"], "garment": job["garment"]})
                if finishes:
                    job["finish"] = d.isoformat()
                    qi += 1
            if items:
                days.append({"date": d.isoformat(), "weekday": d.weekday(),
                             "capacity": round(cap, 1), "used": round(used, 1), "items": items})
        d += timedelta(days=1)
        guard += 1

    job_summary = [{"item": j["item"], "customer": j["customer"], "due": j["due"],
                    "finish": j["finish"], "status": j["status"], "priority": j["priority"],
                    "late": bool(j["due"] and (j["finish"] is None or j["finish"] > j["due"]))}
                   for j in queue]
    return {"craftsman": c, "today": today.isoformat(),
            "days": days, "jobs": job_summary, "no_shift": False}


def craftsman_detail(cid):
    """職人ページ用: 本人・案件一覧・空き予測をまとめて返す。"""
    c = get_craftsman(cid)
    if not c:
        return None
    today = date.today().isoformat()
    jobs = list_jobs(craftsman_id=cid)
    active = [j for j in jobs if j["status"] != "完了"]
    active_hours = round(sum(j["est_hours"] or 0 for j in active), 1)
    caps = [c[col] for col in CAP_COLS]
    forecast = _forecast(active_hours, caps, get_overrides(cid, today))
    return {
        "craftsman": c,
        "today": today,
        "active_count": len(active),
        "active_hours": active_hours,
        "done_count": sum(1 for j in jobs if j["status"] == "完了"),
        "overdue_count": sum(1 for j in active if j["due_date"] and j["due_date"] < today),
        "forecast": forecast,
        "jobs": jobs,
    }


def activity(target_date=None):
    """指定日(既定=今日)に「来た新規案件」と「完了した案件」を返す。"""
    target_date = target_date or date.today().isoformat()
    conn = get_conn()
    name_of = {c["id"]: c["name"] for c in
               conn.execute("SELECT id, name FROM craftsmen").fetchall()}
    new_jobs = [dict(r) for r in conn.execute(
        "SELECT * FROM jobs WHERE substr(created_at,1,10)=? ORDER BY created_at DESC",
        (target_date,)).fetchall()]
    done_jobs = [dict(r) for r in conn.execute(
        "SELECT * FROM jobs WHERE substr(completed_at,1,10)=? ORDER BY completed_at DESC",
        (target_date,)).fetchall()]
    for j in new_jobs + done_jobs:
        j["craftsman_name"] = name_of.get(j["craftsman_id"], "未割当")
    conn.close()
    return {"date": target_date, "new": new_jobs, "done": done_jobs}


if __name__ == "__main__":
    init_db()
    print("DB initialized at", DB_PATH)
