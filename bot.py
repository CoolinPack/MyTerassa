import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

API_TOKEN = "ВАШ_ТОКЕН_БОТА"
ADMIN_GROUP_ID = -1001234567890 
WEB_APP_URL = "URL_ВАШЕГО_RENDER_ПРИЛОЖЕНИЯ"

router = Router()
db_path = "terassa.db"

async def init_db():
    async with aiosqlite.connect(db_path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, birth TEXT, gender TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT, price INTEGER, is_stop INTEGER DEFAULT 0)")
        await db.commit()

@router.message(CommandStart())
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть Terassa Menu", web_app=WebAppInfo(url=WEB_APP_URL))]])
    await message.answer("Добро пожаловать в Terassa! Нажмите кнопку ниже для заказа.", reply_markup=kb)

async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
