#!/usr/bin/env python3
# bot.py - Главный файл запуска бота электрика

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout

from config import BOT_TOKEN
from database.models import init_db
from handlers import start, order, group, admin

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Настройки MTProto прокси (используем HTTP)
MT_PROXY_HOST = "147.125.130.70"
MT_PROXY_PORT = 2083
# Если прокси требует авторизацию, раскомментируйте следующие строки
# MT_PROXY_USER = "username"
# MT_PROXY_PASS = "password"

async def main():
    """Главная функция запуска бота"""
    logger.info("Запуск бота электрика...")
    
    # Инициализация базы данных
    try:
        init_db()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        return
    
    # Настройка таймаутов для стабильной работы
    timeout = ClientTimeout(total=60, connect=30, sock_read=30)
    
    # Создаем сессию с HTTP прокси
    try:
        proxy_url = f"http://{MT_PROXY_HOST}:{MT_PROXY_PORT}"
        
        # Если нужна авторизация, используйте:
        # session = AiohttpSession(
        #     proxy=proxy_url,
        #     proxy_auth=(MT_PROXY_USER, MT_PROXY_PASS),
        #     timeout=timeout
        # )
        
        # Без авторизации:
        session = AiohttpSession(
            proxy=proxy_url,
            timeout=timeout
        )
        
        logger.info(f"Прокси настроен: {proxy_url}")
    except Exception as e:
        logger.error(f"Ошибка настройки прокси: {e}")
        logger.warning("Пробуем прямое подключение без прокси")
        session = AiohttpSession(timeout=timeout)
    
    # Создание объектов бота и диспетчера
    bot = Bot(token=BOT_TOKEN, session=session)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(order.router)
    dp.include_router(group.router)
    dp.include_router(admin.router)
    
    # Проверка подключения к Telegram API
    logger.info("Проверка подключения к Telegram API...")
    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот успешно подключен: @{me.username}")
        logger.info(f"ID бота: {me.id}")
        logger.info(f"Имя бота: {me.full_name}")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Telegram API: {e}")
        logger.error("Бот не может подключиться к Telegram.")
        logger.error("Проверьте:")
        logger.error("1. Доступность прокси сервера")
        logger.error("2. Правильность токена бота")
        logger.error("3. Интернет-соединение")
        return
    
    # Пропускаем накопившиеся обновления и запускаем бота
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удален, накопившиеся обновления пропущены")
    except Exception as e:
        logger.warning(f"Ошибка при удалении webhook: {e}")
    
    logger.info("🚀 Бот успешно запущен и готов к работе!")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()
        logger.info("Сессия бота закрыта")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
