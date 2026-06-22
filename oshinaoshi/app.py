"""お直し職人 仕事量管理 — Webアプリ (Flask)"""
import os
from datetime import timedelta
from flask import (Flask, request, jsonify, send_from_directory,
                   session, redirect, render_template_string)
import db

STATIC = os.path.join(os.path.dirname(__file__), "static")
app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY", "dev-insecure-key-change-me")
app.permanent_session_lifetime = timedelta(days=30)   # 30日ログイン保持

# 合言葉。環境変数 APP_PASSCODE を設定すると認証ON（未設定＝ローカルは認証なし）
PASSCODE = os.environ.get("APP_PASSCODE", "")

db.init_db()
db.backup_db()   # 起動時に自動バックアップ（3年運用のデータ保全）


LOGIN_HTML = """<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ログイン｜お直し管理</title><link rel="stylesheet" href="/static/style.css"></head>
<body><main style="max-width:380px;margin:8vh auto">
<div class="card">
  <h1 style="font-size:20px;margin:0 0 4px">🧵 お直し 仕事量管理</h1>
  <p class="hint">合言葉を入力してください。</p>
  {% if error %}<p style="color:#c0492f;font-size:13px">{{ error }}</p>{% endif %}
  <form method="post">
    <label class="field"><span>合言葉</span>
      <input name="passcode" type="password" autofocus required></label>
    <button type="submit" class="primary">入る</button>
  </form>
</div></main></body></html>"""


@app.before_request
def require_login():
    if not PASSCODE:
        return  # 合言葉未設定なら認証なし
    p = request.path
    if p == "/login" or p.startswith("/static") or p == "/healthz":
        return
    if session.get("authed"):
        return
    if p.startswith("/api/"):
        return jsonify({"error": "login required"}), 401
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("passcode") == PASSCODE:
            session.permanent = True
            session["authed"] = True
            return redirect("/")
        return render_template_string(LOGIN_HTML, error="合言葉が違います")
    return render_template_string(LOGIN_HTML, error="")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/healthz")
def healthz():
    return "ok"


# ---- 画面 ----
@app.route("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(STATIC, path)


@app.route("/c/<int:cid>")
def craftsman_page(cid):
    return send_from_directory(STATIC, "craftsman.html")


# ---- API: 職人 ----
@app.get("/api/craftsmen")
def api_list_craftsmen():
    return jsonify(db.list_craftsmen())


@app.post("/api/craftsmen")
def api_add_craftsman():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "名前を入力してください"}), 400
    cid = db.add_craftsman(name)
    return jsonify({"id": cid}), 201


@app.get("/api/craftsmen/<int:cid>")
def api_get_craftsman(cid):
    c = db.get_craftsman(cid)
    return (jsonify(c), 200) if c else (jsonify({"error": "not found"}), 404)


@app.patch("/api/craftsmen/<int:cid>")
def api_update_craftsman(cid):
    data = request.get_json(force=True)
    if "active" in data:
        db.set_craftsman_active(cid, bool(data["active"]))
    caps = {k: v for k, v in data.items() if k in db.CAP_COLS}
    if caps:
        db.update_capacity(cid, caps)
    return jsonify({"ok": True})


@app.get("/api/craftsmen/<int:cid>/detail")
def api_craftsman_detail(cid):
    d = db.craftsman_detail(cid)
    return (jsonify(d), 200) if d else (jsonify({"error": "not found"}), 404)


@app.get("/api/craftsmen/<int:cid>/schedule")
def api_schedule(cid):
    s = db.daily_schedule(cid)
    return (jsonify(s), 200) if s else (jsonify({"error": "not found"}), 404)


@app.get("/api/craftsmen/<int:cid>/calendar")
def api_calendar(cid):
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    cal = db.month_calendar(cid, year, month)
    return (jsonify(cal), 200) if cal else (jsonify({"error": "not found"}), 404)


@app.post("/api/craftsmen/<int:cid>/calendar/fill")
def api_fill_month(cid):
    data = request.get_json(force=True)
    cal = db.fill_month_from_week1(cid, int(data["year"]), int(data["month"]))
    return (jsonify(cal), 200) if cal else (jsonify({"error": "not found"}), 404)


@app.post("/api/craftsmen/<int:cid>/shift")
def api_set_shift(cid):
    data = request.get_json(force=True)
    day = data.get("date")
    if not day:
        return jsonify({"error": "date required"}), 400
    if data.get("hours") in (None, ""):
        db.clear_shift(cid, day)        # 空欄 = 曜日パターンに戻す
    else:
        db.set_shift(cid, day, data["hours"])
    return jsonify({"ok": True})


# ---- API: 案件 ----
@app.get("/api/jobs")
def api_list_jobs():
    cid = request.args.get("craftsman_id", type=int)
    status = request.args.get("status")
    return jsonify(db.list_jobs(craftsman_id=cid, status=status))


@app.post("/api/jobs")
def api_add_job():
    data = request.get_json(force=True)
    if not (data.get("item") or "").strip():
        return jsonify({"error": "内容(品目)を入力してください"}), 400
    jid = db.add_job(data)
    return jsonify({"id": jid}), 201


@app.patch("/api/jobs/<int:jid>")
def api_update_job(jid):
    data = request.get_json(force=True)
    db.update_job(jid, data)
    return jsonify({"ok": True})


@app.delete("/api/jobs/<int:jid>")
def api_delete_job(jid):
    db.delete_job(jid)
    return jsonify({"ok": True})


# ---- API: ダッシュボード ----
@app.get("/api/dashboard")
def api_dashboard():
    return jsonify(db.dashboard())


@app.get("/api/activity")
def api_activity():
    return jsonify(db.activity(request.args.get("date")))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5055))
    app.run(host="0.0.0.0", port=port, debug=True)
