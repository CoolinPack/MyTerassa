import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

import database
from menu_data import MENU, POPULAR_TODAY

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")
if ADMIN_GROUP_ID:
    ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния FSM
class RegStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_birth = State()
    waiting_for_gender = State()

class OrderStates(StatesGroup):
    waiting_for_promo = State()
    waiting_for_geo = State()

# Клавиатуры главного меню
def main_reply_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Главная"), KeyboardButton(text="Меню")],
            [KeyboardButton(text="Корзина"), KeyboardButton(text="Профиль")]
        ],
        resize_keyboard=True
    )

# Обработчик старта и регистрации
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    if username:
        await database.update_username(user_id, username)
        
    user = await database.get_user(user_id)
    if not user:
        await message.answer(
            "Добро пожаловать в ресторан **Terassa** (Нячанг)!\n\n"
            "Для оформления заказа пожалуйста пройдите короткую регистрацию.\n"
            "Введите ваше **Имя**:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RegStates.waiting_for_name)
    else:
        await message.answer(
            "Рады видеть вас снова в ресторане **Terassa**!",
            parse_mode="Markdown",
            reply_markup=main_reply_kb()
        )

@dp.message(StateFilter(RegStates.waiting_for_name))
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Введите вашу **дату рождения** (например, 30.09.2002):", parse_mode="Markdown")
    await state.set_state(RegStates.waiting_for_birth)

@dp.message(StateFilter(RegStates.waiting_for_birth))
async def reg_birth(message: types.Message, state: FSMContext):
    await state.update_data(birth=message.text.strip())
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Укажите ваш **пол**:", parse_mode="Markdown", reply_markup=kb)
    await state.set_state(RegStates.waiting_for_gender)

@dp.message(StateFilter(RegStates.waiting_for_gender))
async def reg_gender(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username
    
    await database.save_user(
        user_id=user_id,
        username=username,
        name=data["name"],
        birth_date=data["birth"],
        gender=message.text.strip()
    )
    await state.clear()
    await message.answer(
        "Регистрация успешно завершена! Добро пожаловать.",
        reply_markup=main_reply_kb()
    )

# Навигация: Главная
@dp.message(F.text == "Главная")
async def show_home(message: types.Message):
    kb_inline = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Скидки", callback_data="info_discounts"),
         InlineKeyboardButton(text="Акции", callback_data="info_actions"),
         InlineKeyboardButton(text="Промокод", callback_data="info_promo")]
    ])
    
    popular_text = "🔥 **Популярные блюда сегодня:**\n\n"
    for item in POPULAR_TODAY:
        popular_text += f"• **{item['name']}** — {item['price']:,} VND\n"

    await message.answer(
        "🌆 **Terassa — Ресторан в Нячанге**\n\n"
        f"{popular_text}",
        parse_mode="Markdown",
        reply_markup=kb_inline
    )

@dp.callback_query(F.data.startswith("info_"))
async def info_callbacks(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]
    if action == "discounts":
        await callback.answer("Скидки действуют по промокодам и для постоянных гостей (5%).", show_alert=True)
    elif action == "actions":
        await callback.answer("В день рождения дарим скидку или напиток!", show_alert=True)
    elif action == "promo":
        await callback.answer("Введите промокод в корзине перед оформлением заказа.", show_alert=True)

# Навигация: Меню
@dp.message(F.text == "Меню")
async def show_menu(message: types.Message):
    buttons = [[InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")] for cat in MENU.keys()]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📖 **Категории блюд и напитков:**\nВыберите интересующую категорию:", parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data.startswith("cat_"))
async def show_category_items(callback: types.CallbackQuery):
    cat_name = callback.data.replace("cat_", "")
    items = MENU.get(cat_name, [])
    
    user_id = callback.from_user.id
    cart_items = {row["item_name"]: row["quantity"] for row in await database.get_cart(user_id)}

    await callback.message.edit_text(f"📂 Категория: **{cat_name}**", parse_mode="Markdown")
    
    for item in items:
        qty = cart_items.get(item["name"], 0)
        item_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➖", callback_data=f"cart_minus_{item['name']}"),
                InlineKeyboardButton(text=str(qty), callback_data="noop"),
                InlineKeyboardButton(text="➕", callback_data=f"cart_plus_{item['name']}")
            ]
        ])
        await callback.message.answer(
            f"🍽 **{item['name']}** — {item['price']:,} VND\n*Состав:* {item['desc']}",
            parse_mode="Markdown",
            reply_markup=item_kb
        )
    await callback.answer()

@dp.callback_query(F.data == "noop")
async def noop_callback(callback: types.CallbackQuery):
    await callback.answer()

@dp.callback_query(F.data.startswith("cart_plus_") | F.data.startswith("cart_minus_"))
async def modify_cart_item(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    action = parts[1] # plus or minus
    item_name = "_".join(parts[2:])
    
    delta = 1 if action == "plus" else -1
    
    # Находим цену товара в базе меню
    price = 0
    for cat in MENU.values():
        for itm in cat:
            if itm["name"] == item_name:
                price = itm["price"]
                break
        if price: break

    await database.add_to_cart(callback.from_user.id, item_name, price, delta)
    
    # Получаем актуальное количество
    cart_rows = await database.get_cart(callback.from_user.id)
    new_qty = 0
    for r in cart_rows:
        if r["item_name"] == item_name:
            new_qty = r["quantity"]
            break

    new_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➖", callback_data=f"cart_minus_{item_name}"),
            InlineKeyboardButton(text=str(new_qty), callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"cart_plus_{item_name}")
        ]
    ])
    try:
        await callback.message.edit_reply_markup(reply_markup=new_kb)
    except Exception:
        pass
    await callback.answer(f"Корзина обновлена ({item_name}: {new_qty})")

# Навигация: Корзина
@dp.message(F.text == "Корзина")
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    cart = await database.get_cart(user_id)
    
    if not cart:
        await message.answer("🛒 Ваша корзина пуста.")
        return

    text = "🛒 **Ваша корзина:**\n\n"
    total = 0
    for row in cart:
        subtotal = row["price"] * row["quantity"]
        total += subtotal
        text += f"• {row['item_name']} x{row['quantity']} — {subtotal:,} VND\n"

    discount_pct = await database.get_user_discount(user_id)
    if discount_pct > 0:
        total_discounted = int(total * (1 - discount_pct / 100))
        text += f"\nСкидка по промокоду/карте: {discount_pct}%\n"
        text += f"💰 **Итого к оплате:** {total_discounted:,} VND"
    else:
        text += f"\n💰 **Итого к оплате:** {total:,} VND"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 Ввести промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="🛍 Самовывоз", callback_data="checkout_pickup"),
         InlineKeyboardButton(text="🚗 Доставка", callback_data="checkout_delivery")],
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")]
    ])
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "clear_cart")
async def clear_user_cart(callback: types.CallbackQuery):
    await database.clear_cart(callback.from_user.id)
    await callback.message.edit_text("🛒 Корзина очищена.")

@dp.callback_query(F.data == "enter_promo")
async def ask_promo(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите промокод (например, `TERASSA5`):", parse_mode="Markdown")
    await state.set_state(OrderStates.waiting_for_promo)
    await callback.answer()

@dp.message(StateFilter(OrderStates.waiting_for_promo))
async def apply_promo(message: types.Message, state: FSMContext):
    promo = message.text.strip().upper()
    user_id = message.from_user.id
    
    async with aiosqlite.connect(database.DB_NAME) as db:
        if promo == "TERASSA5":
            await db.execute("INSERT OR REPLACE INTO user_discounts (user_id, discount_percent) VALUES (?, 5)", (user_id,))
            await db.commit()
            await message.answer("✅ Промокод принят! Скидка 5% активирована.", reply_markup=main_reply_kb())
        else:
            await message.answer("❌ Неверный промокод.", reply_markup=main_reply_kb())
    await state.clear()

# Оформление заказа (Самовывоз)
@dp.callback_query(F.data == "checkout_pickup")
async def process_pickup(callback: types.CallbackQuery):
    await finalize_order(callback.from_user, "Самовывоз", "Самовывоз из ресторана")
    await callback.message.answer("✅ Заказ оформлен! Ожидайте подтверждения.")
    await callback.answer()

# Оформление заказа (Доставка)
@dp.callback_query(F.data == "checkout_delivery")
async def process_delivery(callback: types.CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Поделиться геопозицией", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await callback.message.answer("Для доставки отправьте вашу геопозицию с помощью кнопки ниже:", reply_markup=kb)
    await state.set_state(OrderStates.waiting_for_geo)
    await callback.answer()

@dp.message(StateFilter(OrderStates.waiting_for_geo), F.location)
async def receive_geo(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    geo_text = f"Доставка (Широта: {lat:.5f}, Долгота: {lon:.5f} (GPS))"
    
    await finalize_order(message.from_user, "Доставка", geo_text)
    await message.answer("✅ Заказ с доставкой успешно принят!", reply_markup=main_reply_kb())
    await state.clear()

async def finalize_order(user: types.User, order_type: str, address_info: str):
    user_id = user.id
    db_user = await database.get_user(user_id)
    name = db_user[2] if db_user else user.full_name
    
    cart = await database.get_cart(user_id)
    if not cart: return
    
    items_summary = []
    total = 0
    items_text_db = ""
    for row in cart:
        sub = row["price"] * row["quantity"]
        total += sub
        items_summary.append(f"{row['item_name']} x{row['quantity']}")
        items_text_db += f"{row['item_name']} × {row['quantity']}, "

    discount_pct = await database.get_user_discount(user_id)
    if discount_pct > 0:
        total = int(total * (1 - discount_pct / 100))

    now_str = datetime.now().strftime("%d.%m.%Y, %H:%M:%S")
    
    # Сохраняем в БД истории
    async with aiosqlite.connect(database.DB_NAME) as db:
        cursor = await db.execute("""
            INSERT INTO orders (user_id, user_name, items_text, total_price, order_type, address_geo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, items_text_db[:-2], total, order_type, address_info, now_str))
        order_id = cursor.lastrowid
        await db.commit()

    await database.clear_cart(user_id)

    # Формируем чек для отправки клиенту в ЛС
    user_receipt = (
        f"Заказ #{order_id}\n"
        f"{now_str}\n\n"
        f"Состав: {', '.join(items_summary)}\n"
        f"Тип: {address_info}\n"
        f"Имя: {name}\n"
        f"Юзер: @{user.username if user.username else 'нет юзера'}\n"
        f"Доставка считается отдельно при отправке\n"
        f"Скидка по промокоду: {discount_pct}%\n"
        f"Итоговая сумма: {total:,} VND\n\n"
        f"📞 Связь с Администратором: @admin_terassa"
    )
    try:
        await bot.send_message(user_id, user_receipt)
    except Exception:
        pass

    # Отправка заявки в админ-группу
    if ADMIN_GROUP_ID:
        admin_text = (
            f"🚨 **НОВЫЙ ЗАКАЗ #{order_id}** 🚨\n\n"
            f"👤 Клиент: {name} (@{user.username or 'нет'})\n"
            f"🆔 ID: {user_id}\n"
            f"📦 Состав: {', '.join(items_summary)}\n"
            f"🏷 Тип: {address_info}\n"
            f"💵 Итого: {total:,} VND\n"
            f"⏰ Время: {now_str}"
        )
        try:
            await bot.send_message(ADMIN_GROUP_ID, admin_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Не удалось отправить в админ-группу: {e}")

# Навигация: Профиль и История заказов
@dp.message(F.text == "Профиль")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    db_user = await database.get_user(user_id)
    if not db_user:
        await message.answer("Сначала пройдите регистрацию через /start")
        return
    
    _, username, name, birth_date, gender, phone, is_admin = db_user
    
    orders = await database.get_orders_history(user_id)
    orders_text = ""
    for o in orders:
        orders_text += f"\n• **Заказ #{o['order_id']}** ({o['created_at']})\n  Состав: {o['items_text']}\n  Сумма: {o['total_price']:,} VND\n  Тип: {o['order_type']}\n"

    admin_status = "ВКЛ" if is_admin else "ВЫКЛ"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔑 Режим администратора: {admin_status}", callback_data="toggle_admin")]
    ])

    profile_text = (
        f"👤 **Профиль**\n\n"
        f"**Имя:** {name}\n"
        f"**Дата рождения:** {birth_date}\n"
        f"**Пол:** {gender}\n"
        f"**Юзернейм:** @{username if username else 'отсутствует'}\n\n"
        f"📜 **История заказов:**\n{orders_text if orders_text else 'История пуста.'}"
    )
    await message.answer(profile_text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "toggle_admin")
async def toggle_admin_mode(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    db_user = await database.get_user(user_id)
    if not db_user: return
    
    current_status = db_user[6]
    new_status = 0 if current_status else 1
    
    async with aiosqlite.connect(database.DB_NAME) as db:
        await db.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (new_status, user_id))
        await db.commit()
        
    status_str = "ВКЛ" if new_status else "ВЫКЛ"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔑 Режим администратора: {status_str}", callback_data="toggle_admin")]
    ])
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await callback.answer(f"Режим администратора: {status_str}")

# Запуск бота
async def main():
    await database.init_db()
    logging.basicConfig(level=logging.INFO)
    print("Бот Terassa успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
