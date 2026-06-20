import re


CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "兩": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

CHINESE_TIME_RE = re.compile(
    r"(?P<period>凌晨|清晨|早上|上午|中午|下午|傍晚|晚上|晚間|夜晚|今晚|明晚)?\s*"
    r"(?P<hour>\d{1,2}|[零〇一二兩三四五六七八九十]{1,3})\s*"
    r"(?:(?:點|点|時|时)(?P<minute>半|\d{1,2})?|[:：](?P<minute_colon>\d{1,2}))"
)

NUMERIC_TIME_RE = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3])[:：](?P<minute>[0-5]\d)(?!\d)")

THAI_TIME_BY_HOUR = {
    0: "เที่ยงคืน",
    1: "ตีหนึ่ง",
    2: "ตีสอง",
    3: "ตีสาม",
    4: "ตีสี่",
    5: "ตีห้า",
    6: "หกโมงเช้า",
    7: "เจ็ดโมงเช้า",
    8: "แปดโมงเช้า",
    9: "เก้าโมงเช้า",
    10: "สิบโมงเช้า",
    11: "สิบเอ็ดโมง",
    12: "เที่ยง",
    13: "บ่ายโมง",
    14: "บ่ายสองโมง",
    15: "บ่ายสามโมง",
    16: "สี่โมงเย็น",
    17: "ห้าโมงเย็น",
    18: "หกโมงเย็น",
    19: "หนึ่งทุ่ม",
    20: "สองทุ่ม",
    21: "สามทุ่ม",
    22: "สี่ทุ่ม",
    23: "ห้าทุ่ม",
}

THAI_HOUR_BY_TIME = {value: key for key, value in THAI_TIME_BY_HOUR.items()}


def parse_chinese_number(value):
    if value.isdigit():
        return int(value)

    if value in CHINESE_DIGITS:
        return CHINESE_DIGITS[value]

    if "十" not in value:
        return None

    left, _, right = value.partition("十")
    tens = CHINESE_DIGITS.get(left, 1) if left else 1
    ones = CHINESE_DIGITS.get(right, 0) if right else 0
    return tens * 10 + ones


def normalize_chinese_time(hour, period):
    if hour is None or hour < 0 or hour > 24:
        return None

    if period in {"下午", "傍晚", "晚上", "晚間", "夜晚", "今晚", "明晚"}:
        if 1 <= hour <= 11:
            return hour + 12
        if hour == 12 and period in {"晚上", "晚間", "夜晚"}:
            return 0
        return hour if hour <= 23 else None

    if period in {"凌晨", "清晨", "早上", "上午"}:
        if hour == 12:
            return 0
        return hour if hour <= 23 else None

    if period == "中午":
        if hour == 12:
            return 12
        return hour if hour <= 23 else None

    return hour if hour <= 23 else None


def parse_time_minute(value, colon_value):
    if value == "半":
        return 30
    if colon_value is not None:
        return int(colon_value)
    if value:
        return int(value)
    return 0


def format_canonical_time(hour, minute):
    return f"{hour:02d}:{minute:02d}"


def thai_time_hint(hour, minute):
    base = THAI_TIME_BY_HOUR.get(hour)
    if not base:
        return format_canonical_time(hour, minute)
    if minute == 0:
        return base
    if minute == 30:
        return f"{base}ครึ่ง"
    return format_canonical_time(hour, minute)


def chinese_time_hint(hour, minute):
    if hour == 0:
        period = "凌晨"
        display_hour = 12
    elif 1 <= hour <= 5:
        period = "凌晨"
        display_hour = hour
    elif 6 <= hour <= 11:
        period = "早上"
        display_hour = hour
    elif hour == 12:
        period = "中午"
        display_hour = 12
    elif 13 <= hour <= 17:
        period = "下午"
        display_hour = hour - 12
    elif hour == 18:
        period = "傍晚"
        display_hour = 6
    else:
        period = "晚上"
        display_hour = hour - 12

    if minute == 0:
        return f"{period}{display_hour}點"
    if minute == 30:
        return f"{period}{display_hour}點半"
    return f"{period}{display_hour}點{minute:02d}分"


def add_time_fact(facts, seen, source, hour, minute):
    if hour is None or minute < 0 or minute > 59:
        return

    key = (source, hour, minute)
    if key in seen:
        return

    seen.add(key)
    facts.append({
        "source": source,
        "hour": hour,
        "minute": minute,
        "canonical": format_canonical_time(hour, minute),
        "thai": thai_time_hint(hour, minute),
        "zh": chinese_time_hint(hour, minute),
    })


def extract_time_facts(text, lang):
    facts = []
    seen = set()

    for match in NUMERIC_TIME_RE.finditer(text):
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        add_time_fact(facts, seen, match.group(0), hour, minute)

    if lang == "zh":
        for match in CHINESE_TIME_RE.finditer(text):
            hour = parse_chinese_number(match.group("hour"))
            hour = normalize_chinese_time(hour, match.group("period"))
            minute = parse_time_minute(match.group("minute"), match.group("minute_colon"))
            add_time_fact(facts, seen, match.group(0).strip(), hour, minute)

    if lang == "th":
        lowered = text.lower()
        used_spans = []
        for thai_time, hour in sorted(THAI_HOUR_BY_TIME.items(), key=lambda item: len(item[0]), reverse=True):
            for match in re.finditer(re.escape(thai_time), lowered):
                span = match.span()
                if any(max(span[0], used[0]) < min(span[1], used[1]) for used in used_spans):
                    continue
                used_spans.append(span)
                add_time_fact(facts, seen, thai_time, hour, 0)

    return facts


def build_protected_facts_prompt(text, lang, target_lang):
    facts = extract_time_facts(text, lang)
    lines = [
        "關鍵資訊保護規則：",
        "- 數字、時間、日期、金額、電話、帳號、網址、人名、地名不可以翻錯、換算錯、四捨五入或自行改寫。",
        "- 遇到時間時，先判斷 24 小時制的真實時間，再翻成目標語言。",
        "- 中文「晚上10點」= 22:00，泰文是「สี่ทุ่ม」；絕對不可以翻成「สองทุ่ม」（20:00）。",
        "- 如果不確定自然時間說法，保留 24 小時制，例如 22:00，比翻錯更好。",
    ]

    if facts:
        lines.append("本次原文偵測到的受保護時間：")
        for fact in facts:
            target_hint = fact["thai"] if target_lang == "th" else fact["zh"]
            lines.append(f"- 「{fact['source']}」= {fact['canonical']}；目標語言可用「{target_hint}」。")

    return "\n".join(lines), facts


def translation_breaks_time_facts(translated, facts, target_lang):
    if not facts:
        return False

    protected_times = {(fact["hour"], fact["minute"]) for fact in facts}
    translated_facts = extract_time_facts(translated, "zh" if target_lang == "zh" else "th")
    for fact in facts:
        if translated_facts and not any(
            item["hour"] == fact["hour"] and item["minute"] == fact["minute"]
            for item in translated_facts
        ):
            return True

        if target_lang == "th":
            expected = thai_time_hint(fact["hour"], fact["minute"])
            has_expected = expected in translated or fact["canonical"] in translated
            wrong_times = [
                time_text
                for hour, time_text in THAI_TIME_BY_HOUR.items()
                if hour != fact["hour"] and time_text in translated
            ]
            if wrong_times and not has_expected:
                return True

    for match in NUMERIC_TIME_RE.finditer(translated):
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        if (hour, minute) not in protected_times:
            return True

    return False
