import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.filters import CommandStart

TOKEN = "ВАШ_ТОКЕН"
ADMIN_GROUP_ID = -1001234567890 # ID вашей группы для заказов
WEB_APP_URL = "https://ваш-сайт.onrender.com"

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Перейти в Terassa Menu", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    await message.answer("Добро пожаловать в Terassa! Закажите лучшие блюда Нячанга.", reply_markup=kb)

# Прием заказа от Mini App
@dp.message(F.content_type == "web_app_data")
async def handle_order(message: Message):
    data = message.web_app_data.data
    await bot.send_message(ADMIN_GROUP_ID, f"🔔 Новый заказ:\n{data}")
    await message.answer("✅ Ваш заказ принят и передан поварам!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
