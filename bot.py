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

# Настройки MTProto прокси
MT_PROXY_HOST = "147.125.130.70"
MT_PROXY_PORT = 2083

async def main():
    """Главная функция запуска бота"""
    logger.info("Запуск бота электрика...")
    
    # Инициализация базы данных
    init_db()
    logger.info("База данных инициализирована")
    
    # Настройка таймаутов для стабильной работы
    timeout = ClientTimeout(total=60, connect=30)
    
    # Создаем сессию с MTProto прокси (только proxy и timeout)
    try:
        session = AiohttpSession(
            proxy=f"socks5://{MT_PROXY_HOST}:{MT_PROXY_PORT}",
            timeout=timeout
        )
        logger.info(f"Прокси настроен: socks5://{MT_PROXY_HOST}:{MT_PROXY_PORT}")
    except Exception as e:
        logger.error(f"Ошибка настройки прокси: {e}")
        # Пробуем без прокси
        session = AiohttpSession(timeout=timeout)
        logger.warning("Прокси не работает, пробуем прямое подключение")
    
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
    try:
        me = await bot.get_me()
        logger.info(f"Бот успешно подключен: @{me.username}")
        logger.info(f"ID бота: {me.id}")
    except Exception as e:
        logger.error(f"Ошибка подключения к Telegram API: {e}")
        logger.error("Бот не может подключиться к Telegram. Проверьте интернет-соединение и настройки прокси.")
        return
    
    # Пропускаем накопившиеся обновления и запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("Бот успешно запущен и готов к работе!")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
