print("RUNNING CLEAN VERSION NO DB")

from fastapi import FastAPI, Request, HTTPException
import requests
import json
import hmac
import base64
import hashlib
import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = "U1d601a0534de8026cab3701de2b33f13"
DATABASE_URL = os.getenv("DATABASE_URL")

client = OpenAI(api_key=OPENAI_API_KEY)
# ======== 語言辨識 ========
def verify_signature(body, signature):
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)

def get_conn():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            plan TEXT DEFAULT 'free',
            used_today INTEGER DEFAULT 0,
            last_used_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    
def detect_language(text):
    thai = sum(1 for c in text if '\u0E00' <= c <= '\u0E7F')
    zh = sum(1 for c in text if '\u4E00' <= c <= '\u9FFF')
    if thai > zh:
        return "th"
    if zh > 0:
        return "zh"
    return "unknown"
# ======== 模型選擇 ========
def choose_model(text):
    return "gpt-4.1"

def translate_text(text):
    lang = detect_language(text)

    if lang == "zh":
        rule = "翻譯成自然、準確、符合泰國日常溝通習慣的泰文"
    elif lang == "th":
        rule = "翻譯成自然、準確、符合台灣使用習慣的繁體中文"
    else:
        return "目前只支援中文或泰文翻譯"

    prompt = f"""
你是專業的繁體中文與泰文雙向翻譯員，專門翻譯 LINE 聊天、日常對話、情侶聊天、朋友玩笑與工作溝通。

翻譯規則：
1. 必須忠實翻譯原意，不可以自行腦補情緒。
2. 不要把禮貌語氣翻成不耐煩、命令、兇或嘲諷。
3. 保留原文的語氣、親密感、曖昧感、玩笑感、吐槽感。
4. 如果原文是口語，譯文也要像 LINE 聊天一樣自然。
5. 不要過度美化、淡化或委婉化。
6. 不要逐字硬翻，但不能改變原本態度。
7. 泰文語氣詞要正確判斷：
   - คะ / ค่ะ / ครับ：多半是禮貌語氣。
   - นะ / นะคะ / นะครับ：多半是柔和、撒嬌、提醒語氣。
   - สิ / สิคะ / สิครับ：多半是「可以啊、當然啊、就...呀」的自然語氣，不要翻成「你自己...啦」。
8. 遇到短句時，優先翻成自然、簡短、精準的聊天語氣。
9. 人名、品牌名、地名、APP 名稱盡量保留原文。
10. 如果是敏感、曖昧、色色、玩笑或吐槽語氣，也要自然且準確翻譯，不要刻意變禮貌。
11. 不要解釋，不要加前言，只輸出最終翻譯結果。

{rule}

原文：
{text}
"""

    try:
        res = client.responses.create(
            model=choose_model(text),
            model="gpt-4.1",
            input=prompt
        )
        return res.output_text.strip()
    except Exception as e:
        print("translate error:", e)
        return "翻譯服務暫時忙碌，請稍後再試。"

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

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def home():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")

    if not verify_signature(body, signature):
        raise HTTPException(status_code=400)

    data = json.loads(body.decode())

    for event in data.get("events", []):

        if event.get("type") == "join":
            reply_token = event["replyToken"]
            reply_message(
                reply_token,
                "大家好，我是泰故事中泰翻譯機器人 🤖\n\n"
                "🔺輸入泰文/中文即可翻譯\n"
                "🔺支援群組自動翻譯\n"
                "🔺未來將推出學泰文 & 對話練習\n"
                "🔺免費版一天限制20次翻譯\n"
                "🔺升級 VIP 可無限翻譯\n"
                "🔺現在VIP試用期：NT$199/月\n\n"
                "🔺พิมพ์ภาษาไทยหรือภาษาจีนเพื่อแปลได้ทันที\n"
                "🔺รองรับการแปลอัตโนมัติในกลุ่ม\n"
                "🔺เร็ว ๆ นี้จะมีฟีเจอร์เรียนภาษาไทยและฝึกบทสนทนา\n"
                "🔺เวอร์ชันฟรี จำกัดการแปลวันละ 20 ครั้ง\n"
                "🔺อัปเกรดเป็น VIP เพื่อแปลได้ไม่จำกัด\n"
                "🔺ตอนนี้ VIP อยู่ในช่วงทดลองใช้งาน: NT$199 / เดือน"
            )
            continue

        if event.get("type") != "message":
            continue
        if event["message"]["type"] != "text":
            continue

        source = event["source"]
        source_type = source.get("type")
        reply_token = event["replyToken"]
        user_text = event["message"]["text"].strip()
        user_text = re.sub(r'@\S+', '', user_text).strip()

        if user_text == "/id":
            user_id = source.get("userId")
            
            reply_message(
                reply_token,
                f"你的 user_id：\n{user_id}"
            )
            continue
        if user_text.startswith("/vip "):
            
            if source.get("userId") != ADMIN_ID:
                reply_message(reply_token, "你沒有權限")
                continue
        
            vip_id = user_text.replace("/vip ", "").strip()

            conn = get_conn()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO users (user_id, plan, used_today, last_used_date)
                VALUES (%s, 'vip', 0, CURRENT_DATE)
                ON CONFLICT (user_id)
                DO UPDATE SET plan='vip'
            """, (vip_id,))

            conn.commit()
            cur.close()
            conn.close()

            reply_message(reply_token, "VIP 開通成功")
            continue
    
        # 群組自動翻譯：不用 / 也能翻
        if source_type == "group":
            text = user_text

            lang = detect_language(text)

            if lang == "unknown":
                continue

            translated = translate_text(text)
            reply_message(reply_token, translated)
            continue
    
        translated = translate_text(user_text)
        reply_message(reply_token, translated)

    return {"status": "ok"}
