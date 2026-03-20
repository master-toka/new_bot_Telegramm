#!/usr/bin/env python3
# bot.py - Версия с настройкой прокси через переменные окружения

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout
import aiohttp

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

async def test_proxy_connection(proxy_url):
    """Тестирует подключение через прокси"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                "https://api.telegram.org",
                proxy=proxy_url
            ) as response:
                return response.status == 200
    except Exception as e:
        logger.debug(f"Тест прокси {proxy_url} не удался: {e}")
        return False

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
    
    # Проверяем доступность прокси
    proxy_url = f"http://{MT_PROXY_HOST}:{MT_PROXY_PORT}"
    proxy_available = await test_proxy_connection(proxy_url)
    
    if proxy_available:
        logger.info(f"✅ Прокси {proxy_url} доступен")
        # Устанавливаем прокси через переменную окружения
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        
        # Создаем сессию с прокси
        timeout = ClientTimeout(total=60, connect=30, sock_read=30)
        session = AiohttpSession(
            proxy=proxy_url,
            timeout=timeout
        )
        bot = Bot(token=BOT_TOKEN, session=session)
    else:
        logger.warning(f"❌ Прокси {proxy_url} недоступен, пробуем прямое подключение")
        timeout = ClientTimeout(total=60, connect=30, sock_read=30)
        session = AiohttpSession(timeout=timeout)
        bot = Bot(token=BOT_TOKEN, session=session)
    
    # Проверяем подключение к Telegram
    try:
        me = await asyncio.wait_for(bot.get_me(), timeout=30)
        logger.info(f"✅ Бот успешно подключен: @{me.username}")
    except asyncio.TimeoutError:
        logger.error("❌ Таймаут подключения к Telegram API")
        return
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Telegram API: {e}")
        return
    
    # Создание диспетчера
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(order.router)
    dp.include_router(group.router)
    dp.include_router(admin.router)
    
    # Пропускаем накопившиеся обновления
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удален")
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
