#!/usr/bin/env python3
# bot.py - Главный файл запуска бота электрика

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout, TCPConnector

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
MT_PROXY_SECRET = "ee1603010200010001fc030386e24c3add68656c702e737465616d706f77657265642e636f6d"

async def main():
    """Главная функция запуска бота"""
    logger.info("Запуск бота электрика...")
    
    # Инициализация базы данных
    init_db()
    logger.info("База данных инициализирована")
    
    # Настройка прокси с таймаутами для стабильной работы
    timeout = ClientTimeout(total=60, connect=30, sock_read=30)
    connector = TCPConnector(ssl=False)  # отключаем проверку SSL для прокси
    
    # Создаем сессию с MTProto прокси
    # Для MTProto используем socks5 прокси (стандартный способ)
    session = AiohttpSession(
        proxy=f"socks5://{MT_PROXY_HOST}:{MT_PROXY_PORT}",
        timeout=timeout,
        connector=connector
    )
    
    # Создание объектов бота и диспетчера с использованием прокси
    bot = Bot(token=BOT_TOKEN, session=session)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(order.router)
    dp.include_router(group.router)
    dp.include_router(admin.router)
    
    # Проверка подключения к Telegram API через прокси
    try:
        me = await bot.get_me()
        logger.info(f"Бот успешно подключен через MTProto прокси: @{me.username}")
    except Exception as e:
        logger.error(f"Ошибка подключения к Telegram API через прокси: {e}")
        logger.error("Проверьте доступность прокси и правильность настроек")
        return
    
    # Пропускаем накопившиеся обновления и запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("Бот успешно запущен и готов к работе!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
