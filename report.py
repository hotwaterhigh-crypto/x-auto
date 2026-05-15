import tweepy
import json
from datetime import datetime
from config import (
    X_API_KEY,
    X_API_SECRET,
    X_ACCESS_TOKEN,
    X_ACCESS_TOKEN_SECRET,
)


def get_client():
    return tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )


def get_account_metrics():
    client = get_client()
    me = client.get_me(user_fields=["public_metrics", "created_at"])
    pm = me.data.public_metrics
    return {
        "username": me.data.username,
        "followers": pm["followers_count"],
        "following": pm["following_count"],
        "tweet_count": pm["tweet_count"],
    }


def get_recent_tweets_metrics(count=25):
    client = get_client()
    me = client.get_me()
    tweets = client.get_users_tweets(
        me.data.id,
        max_results=count,
        tweet_fields=["public_metrics", "created_at"],
        user_auth=True,
    )
    results = []
    if tweets.data:
        for t in tweets.data:
            pm = t.public_metrics
            results.append({
                "id": t.id,
                "text": t.text,
                "created_at": str(t.created_at),
                "impressions": pm.get("impression_count", 0),
                "likes": pm.get("like_count", 0),
                "retweets": pm.get("retweet_count", 0),
                "replies": pm.get("reply_count", 0),
                "quotes": pm.get("quote_count", 0),
            })
    return results


def classify_post(text):
    if "youtube.com/@k_seikeinavi/shorts" in text:
        return "YouTubeショート"
    elif "youtube.com/@k_seikeinavi" in text:
        return "YouTube宣伝"
    elif "kankoku-seikei-navi.com/column/" in text:
        return "コラム宣伝"
    elif "kankoku-seikei-navi.com/event/" in text:
        return "日本相談会"
    else:
        return "輪郭・両顎 情報系"


def calc_engagement_rate(tweet):
    imp = tweet["impressions"]
    if imp == 0:
        return 0
    eng = tweet["likes"] + tweet["retweets"] + tweet["replies"] + tweet["quotes"]
    return round(eng / imp * 100, 2)


def generate_report(count=25):
    account = get_account_metrics()
    tweets = get_recent_tweets_metrics(count)

    print("=" * 55)
    print(f"  @{account['username']} パフォーマンスレポート")
    print(f"  取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    print(f"\n【アカウント概要】")
    print(f"  フォロワー: {account['followers']}")
    print(f"  フォロー: {account['following']}")
    print(f"  総ツイート数: {account['tweet_count']}")

    print(f"\n【直近{len(tweets)}投稿のパフォーマンス】")
    print("-" * 55)

    category_stats = {}
    total_imp = 0
    total_eng = 0

    for i, t in enumerate(tweets):
        cat = classify_post(t["text"])
        eng = t["likes"] + t["retweets"] + t["replies"] + t["quotes"]
        eng_rate = calc_engagement_rate(t)
        total_imp += t["impressions"]
        total_eng += eng

        if cat not in category_stats:
            category_stats[cat] = {"count": 0, "imp": 0, "eng": 0}
        category_stats[cat]["count"] += 1
        category_stats[cat]["imp"] += t["impressions"]
        category_stats[cat]["eng"] += eng

        preview = t["text"].replace("\n", " ")[:45]
        print(f"  {i+1}. [{cat}]")
        print(f"     {preview}...")
        print(f"     IMP:{t['impressions']}  ♥:{t['likes']}  RT:{t['retweets']}  💬:{t['replies']}  ENG率:{eng_rate}%")
        print()

    print("=" * 55)
    print("【カテゴリ別パフォーマンス】")
    print("-" * 55)
    for cat, stats in sorted(category_stats.items(), key=lambda x: x[1]["imp"], reverse=True):
        avg_imp = round(stats["imp"] / stats["count"]) if stats["count"] > 0 else 0
        avg_eng = round(stats["eng"] / stats["count"], 1) if stats["count"] > 0 else 0
        eng_rate = round(stats["eng"] / stats["imp"] * 100, 2) if stats["imp"] > 0 else 0
        print(f"  {cat} ({stats['count']}本)")
        print(f"    合計IMP: {stats['imp']}  平均IMP: {avg_imp}  平均ENG: {avg_eng}  ENG率: {eng_rate}%")

    print()
    print("=" * 55)
    print("【総合サマリ】")
    print(f"  合計インプレッション: {total_imp}")
    print(f"  合計エンゲージメント: {total_eng}")
    overall_rate = round(total_eng / total_imp * 100, 2) if total_imp > 0 else 0
    print(f"  全体ENG率: {overall_rate}%")

    # ベスト・ワースト投稿
    if tweets:
        best = max(tweets, key=lambda x: x["impressions"])
        worst = min(tweets, key=lambda x: x["impressions"])
        print(f"\n  🏆 ベスト投稿 (IMP:{best['impressions']})")
        print(f"     {best['text'].replace(chr(10), ' ')[:50]}...")
        print(f"\n  📉 改善候補 (IMP:{worst['impressions']})")
        print(f"     {worst['text'].replace(chr(10), ' ')[:50]}...")

    print()
    print("=" * 55)

    # レポートをJSONで保存
    report_data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "account": account,
        "tweets": tweets,
        "category_stats": category_stats,
        "total_impressions": total_imp,
        "total_engagement": total_eng,
        "overall_eng_rate": overall_rate,
    }
    filepath = f"reports/report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    import os
    os.makedirs("reports", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"レポート保存: {filepath}")


if __name__ == "__main__":
    generate_report()
