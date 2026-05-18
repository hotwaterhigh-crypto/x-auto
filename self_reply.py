"""
投稿後30分で自リプを追加するスクリプト
最新の自分の投稿に補足情報をリプライする
"""
import json
import os
import subprocess
import tempfile
import tweepy


def get_client():
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def generate_self_reply(original_text):
    """元の投稿に対する自然な自リプを生成"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": f"""以下の投稿に対する自リプ（自分への返信）を1つ作ってください。

元の投稿：
{original_text}

【ルール】
・元の投稿の補足情報、裏話、具体例を追加する
・「ちなみに〜」「補足すると〜」「実は〜」で始める
・100〜140字以内
・自然な人間の言葉で（AI感を出さない）
・宣伝臭なし、URLなし
・投稿文のみ出力。説明不要。""",
            }
        ],
    }

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(payload, tmp, ensure_ascii=False)
    tmp.close()
    try:
        cmd = [
            "curl", "-s", "https://api.anthropic.com/v1/messages",
            "-H", f"x-api-key: {api_key}",
            "-H", "anthropic-version: 2023-06-01",
            "-H", "content-type: application/json",
            "-d", f"@{tmp.name}",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        data = json.loads(r.stdout)
        if "content" in data:
            return data["content"][0]["text"].strip()
        return None
    except Exception as e:
        print(f"自リプ生成エラー: {e}")
        return None
    finally:
        os.unlink(tmp.name)


def main():
    client = get_client()
    me = client.get_me()

    # 最新の自分の投稿を取得
    tweets = client.get_users_tweets(
        me.data.id, max_results=5, user_auth=True
    )

    if not tweets.data:
        print("投稿が見つかりません")
        return

    latest = tweets.data[0]
    print(f"最新投稿: {latest.text[:50]}...")

    # 自リプを生成
    reply_text = generate_self_reply(latest.text)
    if not reply_text:
        print("自リプ生成失敗")
        return

    print(f"自リプ: {reply_text}")

    # リプライとして投稿
    try:
        response = client.create_tweet(
            text=reply_text,
            in_reply_to_tweet_id=latest.id,
        )
        print(f"自リプ投稿成功: {response.data['id']}")
    except Exception as e:
        print(f"自リプ投稿エラー: {e}")


if __name__ == "__main__":
    main()
