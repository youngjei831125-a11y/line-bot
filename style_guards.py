import re


def extract_style_facts(text, lang, target_lang):
    if lang != "zh" or target_lang != "th":
        return []

    facts = []
    normalized = text.replace("！", "!").replace("，", ",")

    if "你們" in text or "你们" in text:
        facts.append({
            "source": "你們",
            "hint": "泰文聊天可省略主詞，或視情境用 ทุกคน / พวกคุณ。",
            "avoid": ["พวกเธอ"],
            "reason": "พวกเธอ 容易變成「你們這群女生」或過度指定對象。",
        })

    if re.search(r"你[們们].*先去|先去", text):
        facts.append({
            "source": "你們可以先去",
            "hint": "自然泰文優先用「ไปกันก่อนได้เลย」。",
            "avoid": ["พวกเธอไปก่อนได้เลย"],
            "reason": "直接翻出 พวกเธอ 會讓語氣變得不自然。",
        })

    if re.search(r"晚[一點一点點点]*到|晚點到|晚点到", normalized):
        facts.append({
            "source": "我晚一點點到",
            "hint": "意思是「我會晚一點抵達」，自然泰文可用「เดี๋ยวเราไปถึงช้านิดนึง」。",
            "avoid": ["ตามไปทีหลังนิดหน่อย"],
            "reason": "ตามไปทีหลังนิดหน่อย 比較像「之後再跟上」，不是「抵達晚一點」。",
        })

    has_eat_something = "吃東西" in text or "吃东西" in text
    has_meal = "吃飯" in text or "吃饭" in text
    if has_eat_something and not has_meal:
        facts.append({
            "source": "吃東西",
            "hint": "吃東西是泛指正在吃東西，自然泰文可用「กำลังกินอะไรอยู่」或「กินอะไรอยู่นิดหน่อย」。",
            "avoid": ["กินข้าว"],
            "reason": "กินข้าว 比較像「吃飯」，會比原文更具體。",
        })

    return facts


def build_style_prompt(text, lang, target_lang):
    facts = extract_style_facts(text, lang, target_lang)
    if lang != "zh" or target_lang != "th":
        return "", facts

    lines = [
        "泰文自然聊天風格規則：",
        "- 中文翻泰文時，不要硬把每個「我、你、你們」都翻出來；泰文自然聊天常省略主詞。",
        "- 「你們」沒有性別資訊時，不要翻成「พวกเธอ」；可省略主詞，或用 ทุกคน / พวกคุณ。",
        "- 「晚一點到、晚點到」是抵達時間比較晚，不是單純之後跟上。",
        "- 「吃東西」不要自動改成「กินข้าว」，除非原文是「吃飯」。",
        "- 譯文要像泰國人 LINE 聊天，不要像教科書或逐字翻譯。",
    ]

    if facts:
        lines.append("本次原文偵測到的自然翻譯提示：")
        for fact in facts:
            avoid = "、".join(f"「{item}」" for item in fact["avoid"])
            lines.append(f"- 「{fact['source']}」：{fact['hint']} 避免使用 {avoid}，因為{fact['reason']}")

    return "\n".join(lines), facts


def translation_breaks_style_facts(translated, facts):
    for fact in facts:
        if any(item in translated for item in fact["avoid"]):
            return True
    return False
