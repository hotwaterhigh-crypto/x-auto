"""
投稿キューが少なくなったら自動で新しい投稿を生成するスクリプト
GitHub Actionsから毎日1回実行される

v3: PDCA反映。体験談系を強化（ENG率1.4%で最高）、リアルレポ紹介継続（IMP169で安定）、問いかけ系継続（IMP191）。リスト系は弱いので体験談に置き換え。
"""
import json
import os
import subprocess
import tempfile
import tweepy

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
QUEUE_FILE = "post_queue.json"
MIN_PENDING = 5  # pending がこの数以下なら補充


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


def search_real_reports():
    """提携クリニックの患者投稿をX APIで検索してリアルレポ紹介用の投稿を生成"""
    try:
        client = tweepy.Client(
            consumer_key=os.environ.get("X_API_KEY", ""),
            consumer_secret=os.environ.get("X_API_SECRET", ""),
            access_token=os.environ.get("X_ACCESS_TOKEN", ""),
            access_token_secret=os.environ.get("X_ACCESS_TOKEN_SECRET", ""),
        )

        clinics = [
            ("DA美容外科", "DA美容外科"),
            ("ドリーム整形外科", "ドリーム整形外科"),
            ("NOTE美容外科", "NOTE美容外科 OR ノート美容外科"),
            ("現代美学美容整形外科", "現代美学美容整形外科"),
            ("ベリーグッド美容外科", "ベリーグッド美容外科 OR ベリーグッド美容"),
        ]

        me = client.get_me()
        my_id = me.data.id
        found = []

        for clinic_name, query in clinics:
            try:
                tweets = client.search_recent_tweets(
                    query=f"{query} -is:retweet lang:ja",
                    max_results=10,
                    tweet_fields=["public_metrics", "created_at", "author_id"],
                    user_auth=True,
                )
                if tweets.data:
                    for t in tweets.data:
                        # 自分の投稿は除外
                        if str(t.author_id) == str(my_id):
                            continue
                        pm = t.public_metrics
                        # 体験談っぽい投稿を優先（術後、経過、DT、ダウンタイムなど）
                        keywords = ["術後", "経過", "DT", "ダウンタイム", "手術", "症例", "レポ", "ビフォー", "カウンセリング"]
                        if any(kw in t.text for kw in keywords):
                            found.append({
                                "clinic": clinic_name,
                                "tweet_id": str(t.id),
                                "text_preview": t.text[:60],
                                "imp": pm.get("impression_count", 0),
                                "likes": pm["like_count"],
                            })
            except Exception as e:
                print(f"  {clinic_name}検索エラー: {e}")

        # IMP順にソートして上位を返す
        found.sort(key=lambda x: x["imp"], reverse=True)
        return found[:5]

    except Exception as e:
        print(f"リアルレポ検索エラー: {e}")
        return []


def generate_real_report_post(report):
    """リアルレポ紹介の投稿テキストを生成"""
    tweet_url = f"https://x.com/i/status/{report['tweet_id']}"
    text = f"""【渡韓整形リアルレポ紹介】

{report['clinic']}で施術を受けられた方のリアルな投稿をご紹介します✨

実際の体験談や経過写真は、検討中の方にとって何よりも参考になりますよね

気になる方はぜひチェックしてみてください💕

#韓国整形 #渡韓整形 #韓国美容整形navi #韓国美容

{tweet_url}"""
    return text


def generate_day_posts(day_number, real_reports=None):
    """1日3本の投稿を生成する（v4: 新アルゴリズム対応）"""

    system = """あなたは韓国美容整形navi（@k_seikeinavi）の中の人として投稿を書いています。
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

【文体ルール（最重要）】
・AIが書いた感じを絶対に出さない。人間の担当者が自分の言葉で書いている感じにする
・テンプレ的な構成（✅箇条書き→CTA）を毎回繰り返さない。バリエーションを持たせる
・「〜ですよね」「〜なんですよ」「〜だったんです」など口語的な語尾を使う
・完璧にまとまった文より、少し崩れた感じの方がリアル
・投稿文のみ出力。説明や補足は不要。"""

    user = f"""以下の3カテゴリで1本ずつ、合計3本の投稿を生成してください。Day{day_number}の投稿です。
前回と内容・切り口・文体が被らないようにしてください。

1. 【08:00 体験談 or 問いかけ】メインの投稿。以下のどちらかで：
   A) 体験談系：相談会に来た方、渡韓した方のリアルなエピソード。感情の変化（不安→安心）を描く。
   B) 問いかけ系：「あなたはどっち？」系の選択肢付き。回答しやすい自然な質問。
   ※「どう思う？」「RTお願い」系のベイト表現は禁止
   ※URLなし。会話が生まれる内容を重視。

2. 【11:00 情報提供 or 豆知識】読むだけで価値がある情報系。以下のどれかで：
   A) 渡韓整形の具体的なTips（費用、ダウンタイム、準備など）
   B) クリニック選びのポイント
   C) 術後の過ごし方
   ※外部リンクは入れない。プロフィールに誘導するなら「詳しくはプロフィールから」程度。

3. 【14:00 相談会 or コラム紹介】以下のどちらかで：
   A) 相談会の魅力を体験ベースで。末尾にURL: https://kankoku-seikei-navi.com/event/
   B) コラム紹介。核心をちら見せ。末尾にURL: https://kankoku-seikei-navi.com/column/
   ※リンクは1投稿に1つまで。

【鉄板テンプレ】Hook（大胆意見や意外な事実）+ 数字 + 体験 → 自然な質問
ハッシュタグ: #韓国整形 #渡韓整形 #韓国美容整形navi ＋内容別1〜2個

出力フォーマット（厳守）:
JSON配列のみ出力。説明不要。

[
  {{"time": "08:00", "type": "main_post", "text": "投稿本文"}},
  {{"time": "11:00", "type": "info_value", "text": "投稿本文"}},
  {{"time": "14:00", "type": "cta_post", "text": "投稿本文"}}
]"""

    result = call_anthropic(system, user)
    if not result:
        return []

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

    # 15:00にリアルレポ紹介を追加
    if real_reports:
        # day_numberに応じてレポートを選択（ローテーション）
        idx = (day_number - 1) % len(real_reports)
        report = real_reports[idx]
        posts.append({
            "day": day_number,
            "time": "15:00",
            "type": "real_report",
            "status": "pending",
            "text": generate_real_report_post(report),
        })
    else:
        # リアルレポが見つからない場合は問いかけ系で埋める
        fallback = call_anthropic(system, f"""Day{day_number}の15:00用に問いかけ系の投稿を1本作れ。
「あなたはどっち？」「コメントで教えて」系の双方向投稿。URLなし。200字以内。
ハッシュタグ付き: #韓国整形 #渡韓整形 #韓国美容整形navi +内容別タグ
投稿文のみ出力。""")
        if fallback:
            posts.append({
                "day": day_number,
                "time": "15:00",
                "type": "engagement_question",
                "status": "pending",
                "text": fallback,
            })

    # 時間順にソート
    time_order = {"10:00": 0, "12:30": 1, "15:00": 2, "18:00": 3, "21:00": 4}
    posts.sort(key=lambda p: time_order.get(p["time"], 9))

    return posts


def main():
    posts = load_queue()
    pending = [p for p in posts if p["status"] == "pending"]
    print(f"現在のキュー: 全{len(posts)}件 / pending {len(pending)}件")

    if len(pending) > MIN_PENDING:
        print(f"pending {len(pending)}件 > {MIN_PENDING}件 → 補充不要")
        return

    print(f"pending {len(pending)}件 <= {MIN_PENDING}件 → 3日分を自動生成")

    # リアルレポ用の患者投稿を検索
    print("リアルレポ用の投稿を検索中...")
    real_reports = search_real_reports()
    print(f"  {len(real_reports)}件の候補を発見")

    next_day = get_next_day(posts)
    generated = 0

    for d in range(next_day, next_day + 3):
        print(f"Day{d} を生成中...")
        new_posts = generate_day_posts(d, real_reports)
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
