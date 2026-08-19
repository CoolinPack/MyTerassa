import aiosqlite
import os

DB_NAME = "terassa.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                birth_date TEXT,
                gender TEXT,
                phone TEXT,
                is_admin INTEGER DEFAULT 0
            )
        """)
        # Таблица корзины (защита от дубликатов через UNIQUE user_id + item_name)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                price INTEGER,
                quantity INTEGER,
                UNIQUE(user_id, item_name)
            )
        """)
        # История заказов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                items_text TEXT,
                total_price INTEGER,
                order_type TEXT,
                address_geo TEXT,
                created_at TEXT
            )
        """)
        # Промокоды и скидки пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_discounts (
                user_id INTEGER PRIMARY KEY,
                discount_percent INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, username, name, birth_date, gender, phone, is_admin FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def save_user(user_id: int, username: str, name: str, birth_date: str, gender: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, name, birth_date, gender, is_admin)
            VALUES (?, ?, ?, ?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                name = excluded.name,
                birth_date = excluded.birth_date,
                gender = excluded.gender
        """, (user_id, username, name, birth_date, gender))
        await db.commit()

async def update_username(user_id: int, username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        await db.commit()

async def get_cart(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT item_name, price, quantity FROM cart WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchall()

async def add_to_cart(user_id: int, item_name: str, price: int, delta: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT quantity FROM cart WHERE user_id = ? AND item_name = ?", (user_id, item_name)) as cursor:
            row = await cursor.fetchone()
        
        if row:
            new_q = row[0] + delta
            if new_q <= 0:
                await db.execute("DELETE FROM cart WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            else:
                await db.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_q, user_id, item_name))
        elif delta > 0:
            await db.execute("INSERT INTO cart (user_id, item_name, price, quantity) VALUES (?, ?, ?, ?)", (user_id, item_name, price, delta))
        await db.commit()

async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_user_discount(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT discount_percent FROM user_discounts WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_orders_history(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY order_id DESC LIMIT 5", (user_id,)) as cursor:
            return await cursor.fetchall()
