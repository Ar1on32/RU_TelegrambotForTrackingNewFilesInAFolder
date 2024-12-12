import os
import time
import logging
import asyncio
import ctypes
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

# Укажите токен вашего бота
TOKEN = 'ВАШ ТОКЕН'
USER_ID = 'ВАШ ID ТЕЛЕГРАМ'  # Ваш Telegram ID

# Папка для отслеживания
WATCH_FOLDER = r'ПУТЬ'  # Укажите путь к папке

# Настройка логирования
logging.basicConfig(level=logging.INFO)

class Watcher:
    def __init__(self, folder_to_watch, bot, loop):
        self.folder_to_watch = folder_to_watch
        self.bot = bot
        self.event_handler = Handler(self.bot, self.folder_to_watch, loop)  # Передаем folder_to_watch в Handler
        self.observer = Observer()

    def run(self):
        self.observer.schedule(self.event_handler, self.folder_to_watch, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

class Handler(FileSystemEventHandler):
    def __init__(self, bot, folder_to_watch, loop):
        self.bot = bot
        self.loop = loop
        self.folder_to_watch = folder_to_watch  # Сохраняем путь к папке

    def on_created(self, event):
        # Создаем асинхронную задачу для отправки сообщения
        asyncio.run_coroutine_threadsafe(self.send_message(event), self.loop)

    async def send_message(self, event):
        if event.is_directory:
            message = f'Новая папка создана: {event.src_path}'
        else:
            # Получаем размер файла в байтах
            file_size = os.path.getsize(event.src_path)
            file_size_mb = file_size / (1024 * 1024)  # Конвертируем в мегабайты
            message = f'Новый файл создан: {event.src_path}\nРазмер файла: {file_size_mb:.2f} МБ'

        # Получаем информацию о свободном месте на диске
        disk_space_info = self.get_disk_space()
        message += f'\nСвободное место на диске: {disk_space_info}'

        await self.bot.send_message(chat_id=USER_ID, text=message)
        logging.info(message)

    def get_disk_space(self):
        """Получаем свободное и общее место на диске в гигабайтах."""
        free_bytes = ctypes.c_ulonglong(0)
        total_bytes = ctypes.c_ulonglong(0)

        # Получаем информацию о диске
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            self.folder_to_watch, 
            ctypes.byref(free_bytes), 
            ctypes.byref(total_bytes), 
            None
        )

        # Конвертируем в гигабайты
        free_gb = free_bytes.value / (1024 * 1024 * 1024)
        total_gb = total_bytes.value / (1024 * 1024 * 1024)

        return f'{free_gb:.2f} ГБ из {total_gb:.2f} ГБ'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен и отслеживает изменения в папке.")

def main():
    # Инициализация бота
    application = ApplicationBuilder().token(TOKEN).build()

    # Создаем новый цикл событий
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Запуск потока для отслеживания изменений в папке
    watcher = Watcher(WATCH_FOLDER, application.bot, loop)  # Передаем loop в Watcher
    watcher_thread = threading.Thread(target=watcher.run)
    watcher_thread.start()

    # Добавление команды /start
    application.add_handler(CommandHandler('start', start))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()