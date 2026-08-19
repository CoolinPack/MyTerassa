import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
import aiosqlite

API_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Замените на токен вашего бота
ADMIN_GROUP_ID = -1001234567890  # ID группы администраторов для заказов
WEB_APP_URL = "https://your-render-app-url.onrender.com"  # URL вашего Web App на Render

db_path = "terassa.db"

async def init_db():
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                phone TEXT,
                name TEXT,
                birth_date TEXT,
                gender TEXT,
                discount REAL DEFAULT 0.0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                category TEXT,
                price INTEGER,
                composition TEXT,
                is_stop INTEGER DEFAULT 0,
                is_popular INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                items TEXT,
                total_price INTEGER,
                order_type TEXT,
                geo TEXT,
                promo TEXT,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                discount REAL
            )
        """)
        await db.commit()
        
        # Заполним начальное меню, если пусто
        async with db.execute("SELECT COUNT(*) FROM menu") as cursor:
            count = (await cursor.fetchone())[0]
            if count == 0:
                initial_menu = [
                    ("Тартар из тунца с авокадо", "Салаты", 160000, "Тунец, авокадо, соус унаги, кунжут", 0, 1),
                    ("Цезарь с креветками", "Салаты", 150000, "Креветки, айсберг, соус цезарь, пармезан, сухарики", 0, 1),
                    ("Лосось на гриле", "Горячее", 150000, "Филе лосося, лимон, травы", 0, 1),
                    ("Цезарь с курицей", "Салаты", 130000, "Куриное филе, айсберг, соус цезарь, пармезан", 0, 0),
                ]
                await db.executemany("""
                    INSERT INTO menu (name, category, price, composition, is_stop, is_popular) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, initial_menu)
                await db.execute("INSERT OR IGNORE INTO promo_codes (code, discount) VALUES ('TERASSA5', 0.05)")
                await db.commit()

class RegStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_birth = State()
    waiting_for_gender = State()
    waiting_for_phone = State()

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT name, phone FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            
            # Обновляем username если изменился
            if user:
                await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
                await db.commit()

    if not user or not user[0]:
        # Требуем регистрацию
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Поделиться номером телефона", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
        await message.answer("Добро пожаловать в **Terassa** Ресторан в Нячанге!\n\nДля доступа к приложению пройдите быструю регистрацию.\nВведите ваше **Имя**:", reply_markup=None)
        await state.set_state(RegStates.waiting_for_name)
    else:
        await send_main_menu(message)

@router.message(RegStates.waiting_for_name)
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите вашу дату рождения (например: 30.09.2002):")
    await state.set_state(RegStates.waiting_for_birth)

@router.message(RegStates.waiting_for_birth)
async def reg_birth(message: Message, state: FSMContext):
    await state.update_data(birth=message.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Укажите ваш пол:", reply_markup=kb)
    await state.set_state(RegStates.waiting_for_gender)

@router.message(RegStates.waiting_for_gender)
async def reg_gender(message: Message, state: FSMContext):
    gender = message.text
    await state.update_data(gender=gender)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Теперь отправьте ваш номер телефона для связи:", reply_markup=kb)
    await state.set_state(RegStates.waiting_for_phone)

@router.message(RegStates.waiting_for_phone, F.contact | F.text)
async def reg_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username
    
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (user_id, username, phone, name, birth_date, gender, discount)
            VALUES (?, ?, ?, ?, ?, ?, 0.05)
        """, (user_id, username, phone, data['name'], data['birth'], data['gender']))
        await db.commit()
        
    await state.clear()
    await message.answer("Регистрация успешно завершена! 🌿", reply_markup=ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True))
    await send_main_menu(message)

async def send_main_menu(message: Message):
    web_app = WebAppInfo(url=WEB_APP_URL)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Открыть Terassa Menu", web_app=web_app)]
    ])
    await message.answer(
        "🌿 **Terassa Ресторан в Нячанге**\n\nНажмите кнопку ниже, чтобы открыть меню, сделать заказ, посмотреть историю и управлять профилем.",
        reply_markup=kb
    )

@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    # Панель управления стоп-листом для администраторов
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT id, name, is_stop FROM menu") as cursor:
            rows = await cursor.fetchall()
            
    kb_list = []
    for row in rows:
        status = "🔴 В стоп-листе" if row[2] == 1 else "🟢 Активно"
        action_text = "Убрать из стоп-листа" if row[2] == 1 else "В стоп-лист"
        callback_data = f"toggle_stop_{row[0]}"
        kb_list.append([InlineKeyboardButton(text=f"{row[1]} ({status})", callback_data=callback_data)])
        
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
    await message.answer("⚙️ **Панель Администратора: Управление стоп-листом блюд**", reply_markup=markup)

@router.callback_query(F.data.startswith("toggle_stop_"))
async def toggle_stop(callback: CallbackQuery):
    dish_id = int(callback.data.split("_")[2])
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT is_stop FROM menu WHERE id = ?", (dish_id,)) as cursor:
            res = await cursor.fetchone()
            if res:
                new_status = 0 if res[0] == 1 else 1
                await db.execute("UPDATE menu SET is_stop = ? WHERE id = ?", (new_status, dish_id))
                await db.commit()
                await callback.answer(f"Статус блюда изменен!")
                await callback.message.edit_text("✅ Статус блюда успешно обновлен в базе данных.")

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
