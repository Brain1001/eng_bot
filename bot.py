# bot.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import router
from database import init_db
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера с хранилищем состояния
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Включаем роутеры с обработчиками
dp.include_router(router)

# Главная функция для запуска бота
async def main():
    logger.info("Инициализация базы данных...")
    init_db()  # Инициализация базы данных при запуске бота
    logger.info("Запуск бота...")
    await dp.start_polling(bot)  # Запуск опроса Telegram API
    logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
