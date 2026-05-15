import random
from config import ACCOUNT_PROFILE

P = ACCOUNT_PROFILE

POST_CATEGORIES = {
    "実績・証拠": {"weight": 20, "time_slots": ["12:30", "19:00"]},
    "ノウハウ・Tips": {"weight": 30, "time_slots": ["08:00", "19:00"]},
    "煽り・問題提起": {"weight": 20, "time_slots": ["12:30", "19:00"]},
    "ツール紹介": {"weight": 15, "time_slots": ["08:00", "19:00"]},
    "マインドセット": {"weight": 15, "time_slots": ["08:00", "19:00"]},
}

if P.get("category_weights"):
    for pair in P["category_weights"].split(","):
        pair = pair.strip()
        if ":" in pair:
            name, w = pair.rsplit(":", 1)
            name = name.strip()
            w = int(w.strip())
            for key in POST_CATEGORIES:
                if name in key or key in name:
                    POST_CATEGORIES[key]["weight"] = w
                    break

SYSTEM_PROMPT = f"""あなたは{P['handle']}として投稿するゴーストライターだ。

【ジャンル】{P['genre']}
【口調】{P['tone']}
【ターゲット】{P['target']}
【ポジショニング】{P['positioning']}
【実績】{P['credential']}

【文体ルール】
・140字以内で完結させろ。途中で切れる文章は絶対禁止。
・改行を効果的に使え。
・絵文字は最小限。
・ハッシュタグ禁止。URL禁止。★●■などの装飾記号禁止。
・同じ内容・同じフレーズの繰り返し禁止。

【NG表現】{P['ng_expressions']}

【ルール】{P['rules']}

【伸びるパターン】{P['top_patterns']}

投稿文のみを出力しろ。説明や補足は一切不要。"""

CATEGORY_PROMPTS = {
    "実績・証拠": f"""{P['handle']}の実績（{P['credential']}）を自然に織り交ぜた投稿を作れ。
自慢にならず、事実ベースで権威性を出せ。
{{phase_context}}Day{{day_number}}の投稿だ。
140字以内で完結する投稿文を出力しろ。途中で切れる文章は禁止。投稿文のみを出力。""",

    "ノウハウ・Tips": f"""{P['genre']}に関する実用的なノウハウやTipsの投稿を作れ。
ターゲット（{P['target']}）がすぐ使える内容にしろ。
{{phase_context}}Day{{day_number}}の投稿だ。
140字以内で完結する投稿文を出力しろ。途中で切れる文章は禁止。投稿文のみを出力。""",

    "煽り・問題提起": f"""{P['genre']}の領域で問題提起する投稿を作れ。
「まだやってないの？」「知らないと損する」系の角度で、ターゲットの行動を促せ。
{{phase_context}}Day{{day_number}}の投稿だ。
140字以内で完結する投稿文を出力しろ。途中で切れる文章は禁止。投稿文のみを出力。""",

    "ツール紹介": f"""{P['genre']}で使えるAIツールや機能を紹介する投稿を作れ。
具体的なツール名を入れて、{P['positioning']}の視点で語れ。
{{phase_context}}Day{{day_number}}の投稿だ。
140字以内で完結する投稿文を出力しろ。途中で切れる文章は禁止。投稿文のみを出力。""",

    "マインドセット": f"""{P['genre']}に取り組む上でのマインドセットを語れ。
{P['handle']}のスタンス（{P['positioning']}）を滲ませろ。
{{phase_context}}Day{{day_number}}の投稿だ。
140字以内で完結する投稿文を出力しろ。途中で切れる文章は禁止。投稿文のみを出力。""",
}


def get_phase_context(day_number):
    if day_number <= 7:
        return "【フェーズ：価値提供期】フォロワーに役立つ情報を全力で出す時期。"
    elif day_number <= 14:
        return "【フェーズ：権威性構築期】実績や数字を見せて信頼を積む時期。"
    elif day_number <= 21:
        return "【フェーズ：期待感醸成期】次のコンテンツへの期待を高める時期。"
    else:
        return "【フェーズ：ローンチ期】行動喚起を強めて成果に繋げる時期。"


def select_category_for_slot(time_slot, day_number):
    available = []
    weights = []
    for cat, info in POST_CATEGORIES.items():
        if time_slot in info["time_slots"]:
            available.append(cat)
            weights.append(info["weight"])
    if not available:
        available = list(POST_CATEGORIES.keys())
        weights = [info["weight"] for info in POST_CATEGORIES.values()]
    return random.choices(available, weights=weights, k=1)[0]


def build_prompt(category, day_number):
    phase_context = get_phase_context(day_number)
    template = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["ノウハウ・Tips"])
    return template.format(day_number=day_number, phase_context=phase_context)
