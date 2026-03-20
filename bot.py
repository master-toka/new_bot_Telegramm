#!/usr/bin/env python3
# bot.py - Альтернативная версия с аутентификацией

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout
from aiohttp_socks import ProxyConnector

from config import BOT_TOKEN
from database.models import init_db
from handlers import start, order, group, admin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Настройки MTProto прокси с секретом
MT_PROXY_HOST = "147.125.130.70"
MT_PROXY_PORT = 2083
# Секрет для MTProto (если требуется)
MT_PROXY_SECRET = "ee1603010200010001fc030386e24c3add68656c702e737465616d706f77657265642e636f6d"

async def main():
    logger.info("Запуск бота электрика...")
    
    try:
        init_db()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        return
    
    timeout = ClientTimeout(total=60, connect=30, sock_read=30)
    
    # Варианты подключения
    connection_methods = [
        {
            "name": "SOCKS5 прокси",
            "connector": ProxyConnector.from_url(f"socks5://{MT_PROXY_HOST}:{MT_PROXY_PORT}")
        },
        {
            "name": "HTTP прокси", 
            "connector": ProxyConnector.from_url(f"http://{MT_PROXY_HOST}:{MT_PROXY_PORT}")
        },
        {
            "name": "Прямое подключение",
            "connector": None
        }
    ]
    
    bot = None
    
    for method in connection_methods:
        try:
            logger.info(f"Пробуем {method['name']}...")
            
            if method['connector']:
                session = AiohttpSession(
                    connector=method['connector'],
                    timeout=timeout
                )
            else:
                session = AiohttpSession(timeout=timeout)
            
            test_bot = Bot(token=BOT_TOKEN, session=session)
            
            # Проверяем подключение с таймаутом
            me = await asyncio.wait_for(test_bot.get_me(), timeout=30)
            logger.info(f"✅ Успешное подключение через {method['name']}: @{me.username}")
            bot = test_bot
            break
            
        except asyncio.TimeoutError:
            logger.warning(f"❌ {method['name']} - таймаут подключения")
        except Exception as e:
            logger.warning(f"❌ {method['name']} - ошибка: {e}")
    
    if not bot:
        logger.error("❌ Не удалось подключиться ни одним из способов")
        logger.error("Проверьте:")
        logger.error("1. Доступность прокси сервера 147.125.130.70:2083")
        logger.error("2. Правильность токена бота")
        logger.error("3. Интернет-соединение")
        return
    
    # Создание диспетчера
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(order.router)
    dp.include_router(group.router)
    dp.include_router(admin.router)
    
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

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
