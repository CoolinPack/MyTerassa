# Terassa Restaurant - Telegram Mini App

Полнофункциональный веб-сервис и Telegram Mini App для ресторана **Terassa** в Нячанге.

## Архитектура и стек
* **Бэкенд**: Python (Aiogram 3, Aiosqlite)
* **Фронтенд**: HTML5, CSS3, JavaScript (Telegram WebApp SDK)
* **База данных**: SQLite (`terassa.db`)
* **Деплой**: GitHub -> Render

## Структура проекта
* `bot.py` — основной файл запуска Telegram-бота, обработчик команд, регистрации и админ-панели (стоп-листы).
* `static/index.html` — главная разметка Mini App (Главная, Меню, Корзина, Профиль).
* `static/style.css` — кастомные стили интерфейса в фирменных бежево-коричневых тонах Terassa.
* `static/script.js` — клиентская логика корзины, фильтрации блюд, поисковика и отправки заказов с геолокацией.

## Развертывание на Render
1. Загрузите файлы в репозиторий GitHub.
2. Создайте новый Web Service на Render, указав репозиторий.
3. Команда запуска (`Start Command`): `python bot.py`
4. Укажите переменные окружения (токен бота).
