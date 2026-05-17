"""
フォロワー数を毎日記録して推移を追跡する
"""
import json
import os
from datetime import datetime

LOG_FILE = "follower_log.json"


def load_log():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_log(log):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def record_followers(followers_count):
    """今日のフォロワー数を記録"""
    log = load_log()
    today = datetime.now().strftime("%Y-%m-%d")

    # 今日のデータがあれば更新、なければ追加
    for entry in log:
        if entry["date"] == today:
            entry["followers"] = followers_count
            save_log(log)
            return

    log.append({"date": today, "followers": followers_count})
    save_log(log)


def get_follower_report():
    """フォロワー推移レポートを生成"""
    log = load_log()
    if not log:
        return "フォロワーデータなし"

    lines = []
    lines.append("【フォロワー推移】")
    lines.append("-" * 40)

    # 直近7日分を表示
    recent = log[-7:]
    for i, entry in enumerate(recent):
        diff_str = ""
        if i > 0:
            diff = entry["followers"] - recent[i - 1]["followers"]
            if diff >= 0:
                diff_str = f" (+{diff})"
            else:
                diff_str = f" ({diff})"
        lines.append(f"  {entry['date']}  {entry['followers']}人{diff_str}")

    # 全期間の変化
    if len(log) >= 2:
        total_diff = log[-1]["followers"] - log[0]["followers"]
        days = len(log)
        avg_daily = round(total_diff / max(days - 1, 1), 1)
        lines.append("")
        lines.append(f"  期間: {log[0]['date']} 〜 {log[-1]['date']} ({days}日間)")
        lines.append(f"  累計変化: {'+' if total_diff >= 0 else ''}{total_diff}人")
        lines.append(f"  日平均: {'+' if avg_daily >= 0 else ''}{avg_daily}人/日")

        # 直近3日のトレンド
        if len(log) >= 3:
            recent_3 = log[-3:]
            trend = recent_3[-1]["followers"] - recent_3[0]["followers"]
            if trend > 0:
                lines.append(f"  直近3日トレンド: 📈 +{trend}人（回復傾向）")
            elif trend < 0:
                lines.append(f"  直近3日トレンド: 📉 {trend}人（減少傾向）")
            else:
                lines.append(f"  直近3日トレンド: ➡️ 変化なし（横ばい）")

    return "\n".join(lines)
