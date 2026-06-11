import os
import json
import httpx
from fastapi import FastAPI, Request, Response
from anthropic import Anthropic

app = FastAPI()
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "goldenbeach2024")

SYSTEM_PROMPT = """Ты — вежливый помощник зоны отдыха Golden Beach Resort в Капчагае (Казахстан).
Отвечай кратко и по делу на русском языке. Используй информацию ниже.

=== ВХОДНЫЕ БИЛЕТЫ ===
Будни / Выходные:
- Взрослый: 9 000 / 10 000 тг
- Подростковый (12–16 лет): 6 000 / 8 000 тг
- Детский (до 12 лет): 4 000 / 5 000 тг
- До 3 лет: БЕСПЛАТНО

=== ГОСТИНИЦА ===
- 2-х местный номер: 45 000 тг
- 4-х местный номер: 70 000 тг
- 5-и местный номер: 80 000 / 90 000 тг (будни/выходные)
- Коттедж (6 чел.): 150 000 / 170 000 тг
- Хостел: 15 000 тг
- Крытая парковка для гостей гостиницы включена

=== ЗОНА ОТДЫХА (1 июня — 31 августа, 10:00–20:00) ===
- Юрта (до 15 чел.): 30 000 тг
- Топчан большой (до 10 чел.): 15 000 тг
- Топчан маленький (до 8 чел.): 12 000 тг
- Пляжный топчан: 12 000 тг
- Оплата за бассейн — отдельно

=== ДОПОЛНИТЕЛЬНЫЕ УСЛУГИ ===
- Шезлонг на пляже: 1 500 тг
- Аренда самовара: 2 000 тг
- Аренда полотенец и простыни: 1 000 тг
- Аренда спорт. инвентаря: 1 000 тг
- Сауна (1 час): 6 000 тг
- Мангал и казан: БЕСПЛАТНО (по очереди)
- Доплата за гостей: взрослые 2 000 тг / дети до 16 лет 1 000 тг

=== ПРАВИЛА ===
Можно приносить: маринад, овощи, воду, детское питание
Запрещено: алкоголь, готовые блюда, кальяны, собственные продукты и напитки
Шампуры, уголь, дрова — не предоставляются
Уличная парковка бесплатно для всех гостей

=== КОНТАКТЫ ===
Instagram: @goldenbeach_qapshagai
Адрес: Капчагай, Казахстан

Если вопрос не по теме или ты не знаешь ответа — вежливо скажи что уточнишь у менеджера и дай контакт Instagram."""

conversation_history = {}

def get_reply(phone: str, user_message: str) -> str:
    if phone not in conversation_history:
        conversation_history[phone] = []
    
    conversation_history[phone].append({
        "role": "user",
        "content": user_message
    })
    
    # Keep only last 10 messages to save memory
    if len(conversation_history[phone]) > 10:
        conversation_history[phone] = conversation_history[phone][-10:]
    
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=conversation_history[phone]
    )
    
    reply = response.content[0].text
    conversation_history[phone].append({
        "role": "assistant",
        "content": reply
    })
    
    return reply

def send_whatsapp_message(to: str, text: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    httpx.post(url, headers=headers, json=data)

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    return Response(content="Forbidden", status_code=403)

@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" not in value:
            return {"status": "ok"}
        
        message = value["messages"][0]
        phone = message["from"]
        
        if message["type"] == "text":
            user_text = message["text"]["body"]
            reply = get_reply(phone, user_text)
            send_whatsapp_message(phone, reply)
    except Exception as e:
        print(f"Error: {e}")
    
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "Golden Beach Bot is running!"}
