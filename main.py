from fastapi import FastAPI, Request, HTTPException
import requests
import json
import hmac
import base64
import hashlib
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def verify_signature(body, signature):
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)

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
        rule = "翻譯成自然、準確、符合泰國日常溝通習慣的泰文"
    elif lang == "th":
        rule = "翻譯成自然、準確、符合台灣使用習慣的繁體中文"
    else:
        return "目前只支援中文或泰文翻譯"

    prompt = f"""
你是一位專業的繁體中文與泰文雙向翻譯員。
請優先準確傳達原意，避免誤會。
不要解釋，不要加前言，只輸出最終翻譯結果。

{rule}

{text}
"""

    try:
        res = client.responses.create(
            model="gpt-4.1-mini",
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
                "私聊可直接輸入中文或泰文\n"
                "群組請在句子前加 /\n\n"
                "例如：\n"
                "/你好\n"
                "/คิดถึงนะ"
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

        if source_type == "group":
            if not user_text.startswith("/"):
                continue
            text = user_text[1:].strip()
            if not text:
                reply_message(reply_token, "請在 / 後輸入要翻譯的內容")
                continue
            translated = translate_text(text)
            reply_message(reply_token, translated)
            continue

        translated = translate_text(user_text)
        reply_message(reply_token, translated)

    return {"status": "ok"}