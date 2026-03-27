from fastapi import FastAPI, Request, HTTPException
import requests
import sqlite3
import json
import hmac
import base64
import hashlib
import os
from datetime import datetime, date
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_NAME = "bot.db"

# ========= 資料庫 =========
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        plan TEXT DEFAULT 'free',
        used_today INTEGER DEFAULT 0,
        last_used_date TEXT
    )
    """)

    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_NAME)

def ensure_user_exists(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, used_today, last_used_date) VALUES (?,0,?)",
            (user_id, str(date.today()))
        )
        conn.commit()
    conn.close()

# ========= 驗證 =========
def verify_signature(body, signature):
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)

# ========= 翻譯 =========
def detect_language(text):
    thai = sum(1 for c in text if '\u0E00' <= c <= '\u0E7F')
    zh = sum(1 for c in text if '\u4E00' <= c <= '\u9FFF')
    if thai > zh:
        return "th"
    if zh > 0:
        return "zh"
    return "unknown"

def translate_text(text):
    lang = detect_language(text)

    if lang == "zh":
        rule = "翻譯成自然泰文"
    elif lang == "th":
        rule = "翻譯成自然繁體中文"
    else:
        return "目前只支援中泰翻譯"

    prompt = f"""
你是一位專業翻譯員
請準確翻譯，不要多說任何話

{rule}

{text}
"""

    res = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return res.output_text.strip()

# ========= LINE =========
def reply_message(token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "replyToken": token,
        "messages": [{"type": "text", "text": text[:5000]}]
    }
    requests.post(url, headers=headers, json=data)

# ========= API =========
@app.get("/")
def home():
    return {"status": "ok"}

@app.on_event("startup")
def startup():
    init_db()

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")

    if not verify_signature(body, signature):
        raise HTTPException(status_code=400)

    data = json.loads(body.decode())

    for event in data.get("events", []):

        # ===== 加入群組提示 =====
        if event.get("type") == "join":
            reply_token = event["replyToken"]
            reply_message(
                reply_token,
                "大家好，我是中泰翻譯機器人 🤖\n\n"
                "👉 用法：在句子前加 /\n\n"
                "例如：\n"
                "/你好\n"
                "/คิดถึงนะ"
            )
            continue

        # ===== 只處理文字 =====
        if event.get("type") != "message":
            continue
        if event["message"]["type"] != "text":
            continue

        source = event["source"]
        source_type = source.get("type")
        user_id = source.get("userId", "unknown")
        group_id = source.get("groupId")
        reply_token = event["replyToken"]
        user_text = event["message"]["text"].strip()

        ensure_user_exists(user_id)

        # ===== 群組邏輯（只用 /）=====
        if source_type == "group" and group_id:

            if not user_text.startswith("/"):
                continue

            text = user_text[1:].strip()

            if not text:
                reply_message(reply_token, "請在 / 後輸入文字")
                continue

            translated = translate_text(text)
            reply_message(reply_token, translated)
            continue

        # ===== 一對一 =====
        translated = translate_text(user_text)
        reply_message(reply_token, translated)

    return {"status": "ok"}