import requests
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from bs4 import BeautifulSoup
import re

parsing_tasks = {}

def parse_website():
    url = "https://funpay.com/lots/2822/"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        descriptions = soup.find_all("div", class_="tc-desc-text")
        pattern = re.compile(r"#\d+([\.,]\d+)?")
        matching_items = []

        for desc in descriptions:
            text = desc.get_text(strip=True)
            match = pattern.search(text)
            if match:
                number_str = match.group(0).replace("#", "").replace(",", "").replace(".", "")
                number = int(number_str)

                if number <= 100:
                    price_element = desc.find_parent().find_next_sibling("div", class_="tc-price")
                    if price_element and price_element.has_attr("data-s"):
                        price = round(float(price_element["data-s"]))
                    else:
                        price = "Цена не указана"

                    parent_link = desc.find_parent("a", class_="tc-item")
                    if parent_link and parent_link.has_attr("href"):
                        link = parent_link["href"]
                        if not link.startswith("http"):
                            link = "https://funpay.com" + link
                    else:
                        link = "Ссылка не найдена"

                    matching_items.append(f"#{number} | {price} ₽ | {link}")

        if matching_items:
            return "\n".join(matching_items)
        else:
            return "Нет подходящих товаров."
    else:
        return "Ошибка при получении данных с сайта"

async def scheduled_parsing(chat_id, context: ContextTypes.DEFAULT_TYPE):
    while True:
        result = parse_website()
        await context.bot.send_message(chat_id=chat_id, text=result)
        await asyncio.sleep(600)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global parsing_tasks
    keyboard = [["Start", "Stop"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

    chat_id = update.message.chat_id
    if chat_id not in parsing_tasks:
        parsing_tasks[chat_id] = asyncio.create_task(scheduled_parsing(chat_id, context))
        await update.message.reply_text("Бот запущен! Парсинг будет выполняться каждые 10 минут.")
    else:
        await update.message.reply_text("Парсинг уже запущен для этого чата.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global parsing_tasks
    user_input = update.message.text
    chat_id = update.message.chat_id

    if user_input == "Start":
        if chat_id not in parsing_tasks:
            parsing_tasks[chat_id] = asyncio.create_task(scheduled_parsing(chat_id, context))
            await update.message.reply_text("Бот запущен! Парсинг будет выполняться каждые 10 минут.")
        else:
            await update.message.reply_text("Парсинг уже запущен для этого чата.")
    elif user_input == "Stop":
        if chat_id in parsing_tasks:
            parsing_tasks[chat_id].cancel()
            del parsing_tasks[chat_id]
            await update.message.reply_text("Бот остановлен! Парсинг прекращен.")
        else:
            await update.message.reply_text("Парсинг не был запущен для этого чата.")

if __name__ == "__main__":
    TOKEN = "UR Token"

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    app.run_polling()
