"""
post_queue.jsonからスマホで見やすいHTMLスケジュールページを生成する
"""
import json

def generate_html():
    with open("post_queue.json", "r", encoding="utf-8") as f:
        posts = json.load(f)

    # Day別にグループ化
    days = {}
    for p in posts:
        d = p["day"]
        if d not in days:
            days[d] = []
        days[d].append(p)

    # 時間順ソート
    for d in days:
        days[d].sort(key=lambda x: x["time"])

    type_labels = {
        "info_contour": "📊 輪郭情報",
        "engagement": "💬 改善版",
        "engagement_A": "💬 問いかけ",
        "engagement_B": "💬 体験談",
        "engagement_C": "📝 リスト",
        "engagement_list": "📝 リスト",
        "engagement_question": "💬 問いかけ",
        "youtube": "🎬 YouTube",
        "youtube_short": "📱 ショート",
        "column": "📰 コラム",
        "event": "🏥 相談会",
        "event_story": "🏥 相談会/体験談",
        "real_report": "🔥 リアルレポ",
    }

    html = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📅 投稿スケジュール - @k_seikeinavi</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #fff0f5; padding: 16px; }
h1 { font-size: 20px; text-align: center; color: #e8649a; margin-bottom: 16px; }
.summary { background: white; border-radius: 12px; padding: 14px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; font-size: 14px; color: #555; }
.summary b { color: #e8649a; font-size: 18px; }
.day { background: white; border-radius: 12px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }
.day-header { background: #e8649a; color: white; padding: 10px 16px; font-size: 16px; font-weight: bold; }
.post { padding: 12px 16px; border-bottom: 1px solid #f5f5f5; }
.post:last-child { border-bottom: none; }
.post-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.time { font-weight: bold; color: #333; font-size: 15px; }
.type { font-size: 12px; background: #fff0f5; color: #e8649a; padding: 2px 8px; border-radius: 10px; }
.status-posted { font-size: 11px; color: white; background: #4CAF50; padding: 2px 8px; border-radius: 10px; }
.status-pending { font-size: 11px; color: white; background: #FF9800; padding: 2px 8px; border-radius: 10px; }
.text { font-size: 13px; color: #555; line-height: 1.5; white-space: pre-wrap; max-height: 80px; overflow: hidden; }
.text.expanded { max-height: none; }
.expand-btn { font-size: 12px; color: #e8649a; cursor: pointer; margin-top: 4px; display: inline-block; }
</style>
</head>
<body>
<h1>📅 @k_seikeinavi 投稿スケジュール</h1>
"""

    posted = len([p for p in posts if p["status"] == "posted"])
    pending = len([p for p in posts if p["status"] == "pending"])
    html += f'<div class="summary">投稿済 <b>{posted}</b>件 ／ 未投稿 <b>{pending}</b>件 ／ 全 <b>{len(posts)}</b>件</div>\n'

    for d in sorted(days.keys()):
        day_posts = days[d]
        posted_count = len([p for p in day_posts if p["status"] == "posted"])
        total_count = len(day_posts)
        html += f'<div class="day">\n'
        html += f'<div class="day-header">📅 Day {d}（{posted_count}/{total_count} 投稿済）</div>\n'

        for p in day_posts:
            label = type_labels.get(p["type"], p["type"])
            status_class = "status-posted" if p["status"] == "posted" else "status-pending"
            status_text = "✅ 投稿済" if p["status"] == "posted" else "⏳ 未投稿"
            preview = p["text"][:100].replace("<", "&lt;").replace(">", "&gt;")

            html += f'<div class="post">\n'
            html += f'  <div class="post-header">\n'
            html += f'    <span class="time">⏰ {p["time"]}</span>\n'
            html += f'    <span class="type">{label}</span>\n'
            html += f'    <span class="{status_class}">{status_text}</span>\n'
            html += f'  </div>\n'
            html += f'  <div class="text" onclick="this.classList.toggle(\'expanded\')">{preview}...</div>\n'
            html += f'  <span class="expand-btn" onclick="this.previousElementSibling.classList.toggle(\'expanded\')">▼ もっと見る</span>\n'
            html += f'</div>\n'

        html += '</div>\n'

    html += """
<script>
document.querySelectorAll('.expand-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = btn.previousElementSibling;
    text.classList.toggle('expanded');
    btn.textContent = text.classList.contains('expanded') ? '▲ 閉じる' : '▼ もっと見る';
  });
});
</script>
</body>
</html>"""

    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("スケジュールページ生成完了: docs/index.html")


if __name__ == "__main__":
    import os
    os.makedirs("docs", exist_ok=True)
    generate_html()
