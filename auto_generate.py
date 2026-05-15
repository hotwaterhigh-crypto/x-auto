"""
投稿キューが少なくなったら自動で新しい投稿を生成するスクリプト
GitHub Actionsから毎日1回実行される
"""
import json
import os
import subprocess
import tempfile

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
QUEUE_FILE = "post_queue.json"
MIN_PENDING = 7  # pending がこの数以下なら補充


def load_queue():
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(posts):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def get_next_day(posts):
    if not posts:
        return 1
    return max(p["day"] for p in posts) + 1


def call_anthropic(system_prompt, user_prompt):
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(payload, tmp, ensure_ascii=False)
    tmp.close()
    try:
        cmd = [
            "curl", "-s", "https://api.anthropic.com/v1/messages",
            "-H", f"x-api-key: {ANTHROPIC_API_KEY}",
            "-H", "anthropic-version: 2023-06-01",
            "-H", "content-type: application/json",
            "-d", f"@{tmp.name}",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        data = json.loads(r.stdout)
        if "content" in data:
            return data["content"][0]["text"].strip()
        print(f"API応答エラー: {r.stdout[:200]}")
        return None
    except Exception as e:
        print(f"API呼び出しエラー: {e}")
        return None
    finally:
        os.unlink(tmp.name)


def generate_day_posts(day_number):
    """1日7本の投稿を生成する"""

    system = """あなたは韓国美容整形navi（@k_seikeinavi）のSNS運用担当です。
ジャンル: 韓国美容整形の渡韓サポート・情報メディア
ターゲット: 20代後半〜40代女性、韓国美容整形を検討している層
提携クリニック: DA美容外科、ドリーム整形外科、NOTE美容外科、現代美学美容整形外科、ベリーグッド美容外科
提携名医: イム・ヨンミン代表院長（ベリーグッド・経歴20年・ソウル聖母病院出身）、ユ・ジハン代表院長（NOTE美容外科・輪郭形成エキスパート）
価格例: 韓国の輪郭3点は約1,400万ウォン、日本は約2,800万ウォン

【絶対ルール】
・345整形外科、パク・ジョンリムは出さない
・院長名にはクリニック名を必ず併記
・効果効能の断定表現禁止。医療広告ガイドライン準拠
・各投稿200字以内
・投稿文のみ出力。説明や補足は不要。"""

    user = f"""以下の7カテゴリで1本ずつ、合計7本の投稿を生成してください。Day{day_number}の投稿です。

1. 【08:00 輪郭・両顎情報系】専門的な施術解説。輪郭3点、両顎、エラ、頬骨、Vラインなどのテーマから1つ選んで解説。
2. 【10:00 改善版】問いかけ系・体験談系・保存リスト系のいずれか。「コメントで教えて」「保存して」のCTA付き。URLなし。
3. 【12:30 YouTube宣伝】韓国美容整形naviのYouTubeチャンネル宣伝。末尾にURL: https://www.youtube.com/@k_seikeinavi
4. 【15:00 改善版】問いかけ系・体験談系・保存リスト系のいずれか（10:00と違う種類）。URLなし。
5. 【18:00 YouTubeショート宣伝】ショート動画宣伝。末尾にURL: https://www.youtube.com/@k_seikeinavi/shorts
6. 【20:00 コラム宣伝】韓国美容整形naviのコラム記事宣伝。末尾にURL: https://kankoku-seikei-navi.com/column/
7. 【21:30 日本相談会】日本で開催する来日相談会の魅力訴求。末尾にURL: https://kankoku-seikei-navi.com/event/

全投稿の末尾にハッシュタグを付けてください: #韓国整形 #渡韓整形 #韓国美容整形navi ＋内容に合ったタグ1〜2個（#輪郭整形 #輪郭3点 #鼻整形 #両顎手術 #小顔整形 #韓国美容 など）

出力フォーマット（厳守）:
各投稿を以下のJSON形式で出力してください。JSON配列のみ出力。説明不要。

[
  {{"time": "08:00", "type": "info_contour", "text": "投稿本文"}},
  {{"time": "10:00", "type": "engagement", "text": "投稿本文"}},
  {{"time": "12:30", "type": "youtube", "text": "投稿本文"}},
  {{"time": "15:00", "type": "engagement", "text": "投稿本文"}},
  {{"time": "18:00", "type": "youtube_short", "text": "投稿本文"}},
  {{"time": "20:00", "type": "column", "text": "投稿本文"}},
  {{"time": "21:30", "type": "event", "text": "投稿本文"}}
]"""

    result = call_anthropic(system, user)
    if not result:
        return []

    # JSON部分を抽出
    try:
        start = result.index("[")
        end = result.rindex("]") + 1
        posts_data = json.loads(result[start:end])
    except (ValueError, json.JSONDecodeError) as e:
        print(f"JSON解析エラー: {e}")
        print(f"生成結果: {result[:300]}")
        return []

    posts = []
    for p in posts_data:
        posts.append({
            "day": day_number,
            "time": p["time"],
            "type": p["type"],
            "status": "pending",
            "text": p["text"],
        })
    return posts


def main():
    posts = load_queue()
    pending = [p for p in posts if p["status"] == "pending"]
    print(f"現在のキュー: 全{len(posts)}件 / pending {len(pending)}件")

    if len(pending) > MIN_PENDING:
        print(f"pending {len(pending)}件 > {MIN_PENDING}件 → 補充不要")
        return

    print(f"pending {len(pending)}件 <= {MIN_PENDING}件 → 3日分を自動生成")

    next_day = get_next_day(posts)
    generated = 0

    for d in range(next_day, next_day + 3):
        print(f"Day{d} を生成中...")
        new_posts = generate_day_posts(d)
        if new_posts:
            posts.extend(new_posts)
            generated += len(new_posts)
            print(f"  {len(new_posts)}件生成")
        else:
            print(f"  生成失敗")

    if generated > 0:
        save_queue(posts)
        print(f"合計{generated}件を追加。キュー更新完了。")
    else:
        print("生成失敗。キュー変更なし。")


if __name__ == "__main__":
    main()
