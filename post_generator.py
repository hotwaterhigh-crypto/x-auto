import json, subprocess, tempfile, os, time
from config import ANTHROPIC_API_KEY
from prompts import SYSTEM_PROMPT, build_prompt, select_category_for_slot


def generate_post_anthropic(category, day_number):
    user_prompt = build_prompt(category, day_number)
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 300,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(payload, tmp, ensure_ascii=False)
    tmp.close()
    try:
        cmd = (
            f'/usr/bin/curl -s https://api.anthropic.com/v1/messages '
            f'-H "x-api-key: {ANTHROPIC_API_KEY}" '
            f'-H "anthropic-version: 2023-06-01" '
            f'-H "content-type: application/json" '
            f'-d @{tmp.name}'
        )
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        if not r.stdout.strip():
            return None
        data = json.loads(r.stdout)
        if "content" in data:
            return data["content"][0]["text"].strip()
        return None
    except:
        return None
    finally:
        os.unlink(tmp.name)


def is_complete_post(text):
    if not text or text == "投稿生成に失敗":
        return False
    if len(text) > 140:
        return False
    bad_endings = [
        "完", "自", "他", "読ん", "書いて", "感動",
        "こ", "プ", "なりた", "人にな", "仕組み作って",
    ]
    for be in bad_endings:
        if text.endswith(be):
            return False
    last_char = text[-1]
    good_endings = list(
        "るただいくすぞなよねかれんむえうろめてにをはもがぜさけせつみりし？！…。らので"
    )
    if last_char in good_endings:
        return True
    return False


def generate_post(category, day_number):
    text = None
    for attempt in range(5):
        text = generate_post_anthropic(category, day_number)
        if text and is_complete_post(text):
            return text
        if text and len(text) > 140:
            print(f"  {len(text)}字 再生成({attempt+1}/5)")
            time.sleep(1)
    if text and len(text) > 140:
        lines = text.split("\n")
        result = ""
        for line in lines:
            if len(result + line + "\n") <= 140:
                result += line + "\n"
            else:
                break
        return result.strip() if result.strip() else text[:140]
    return text if text else "投稿生成に失敗"


def generate_daily_posts(day_number, time_slots):
    posts = []
    used_categories = []
    for slot in time_slots:
        for _ in range(10):
            category = select_category_for_slot(slot, day_number)
            if category not in used_categories or len(used_categories) >= 4:
                break
        used_categories.append(category)
        text = generate_post(category, day_number)
        posts.append({
            "time": slot,
            "category": category,
            "text": text,
            "day": day_number,
        })
        print(f"  [{slot}] {category} ({len(text)}字): {text[:50]}…")
    return posts


def generate_batch_posts(start_day, end_day, time_slots):
    all_posts = []
    for day in range(start_day, end_day + 1):
        print(f"Day {day} の投稿を生成中…")
        daily = generate_daily_posts(day, time_slots)
        all_posts.extend(daily)
    return all_posts


def save_posts_to_json(posts, filepath="post_queue.json"):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"{len(posts)}件の投稿を {filepath} に保存")


def load_posts_from_json(filepath="post_queue.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
