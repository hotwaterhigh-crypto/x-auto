"""
GitHub Actions用 自動投稿スクリプト
指定時間帯に合った投稿をpost_queue.jsonから取得して投稿する
"""
import json
import os
import sys
import tweepy
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def get_client():
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def load_queue(filepath="post_queue.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(posts, filepath="post_queue.json"):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def find_post_for_slot(posts, time_slot):
    """指定時間帯のpending投稿を1つ返す"""
    for p in posts:
        if p["time"] == time_slot and p["status"] == "pending":
            return p
    return None


def post_tweet(text):
    client = get_client()
    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        me = client.get_me()
        url = f"https://x.com/{me.data.username}/status/{tweet_id}"
        print(f"投稿成功: {url}")
        return True
    except Exception as e:
        print(f"投稿失敗: {e}")
        return False


def main():
    # 現在のJST時刻から時間帯を判定
    now = datetime.now(JST)
    current_hour = now.hour
    current_minute = now.minute

    # 時間帯マッピング（GitHub Actionsのcronから呼ばれる）
    time_slots = {
        (7, 50): "08:00",
        (9, 50): "10:00",
        (12, 20): "12:30",
        (14, 50): "15:00",
        (17, 50): "18:00",
        (19, 50): "20:00",
        (21, 20): "21:30",
    }

    # 一番近い時間帯を探す
    target_slot = None
    for (h, m), slot in time_slots.items():
        if abs(current_hour - h) <= 1 and abs(current_minute - m) <= 15:
            target_slot = slot
            break

    # コマンドライン引数で時間帯を指定することも可能
    if len(sys.argv) > 1:
        target_slot = sys.argv[1]

    if not target_slot:
        print(f"現在時刻 {now.strftime('%H:%M')} に対応する投稿枠なし")
        return

    print(f"投稿枠: {target_slot} (JST: {now.strftime('%Y-%m-%d %H:%M')})")

    posts = load_queue()
    post = find_post_for_slot(posts, target_slot)

    if not post:
        print(f"{target_slot} のpending投稿なし")
        return

    print(f"Day{post['day']} [{post['type']}] を投稿...")
    success = post_tweet(post["text"])

    if success:
        post["status"] = "posted"
        post["posted_at"] = now.strftime("%Y-%m-%d %H:%M")
        save_queue(posts)
        print("キュー更新完了")


if __name__ == "__main__":
    main()
