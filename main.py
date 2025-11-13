import os
import pytz
import zipfile
import shutil
import asyncio
import tempfile
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramRetryAfter


from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer


from config import (
    BOT_TOKEN,
    OUTPUT_CHANNEL_LOGS_ID,
    OUTPUT_CHANNEL_TXT_ID,
    GOOGLE_SHEET_URL,
    ADMIN_IDS,
    COUNTERS_DIR,
)
from just_cleaner import main_cleaner
from utils.bot_utils import (
    get_all_files_in_archive,
    sanitize_sheet_name,
    init_google_sheets,
    get_or_create_sheet,
    write_to_sheet,
    _extract_rar,
    zip_folder,
)
from utils.miti_utils import (
    choose_tag_for_destination,
    _reset_counters_for_date,
    generate_pack_name,
)
from utils.file_utils import is_mails_archive, is_logs_archive
from queue_manager import init_process_queue, get_process_queue, ProcessTask


LOCAL_API_SERVER = "http://localhost:8081"
local_api = TelegramAPIServer.from_base(LOCAL_API_SERVER, is_local=True)
session = AiohttpSession(api=local_api)
COUNTERS_DIR.mkdir(parents=True, exist_ok=True)
bot = Bot(token=BOT_TOKEN)  # , session=session
dp = Dispatcher(storage=MemoryStorage())


async def safe_edit(message: Message, text: str):
    if message is None:
        return
    try:
        await message.edit_text(text)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after + 0.5)
        try:
            await message.edit_text(text)
        except:
            pass
    except Exception as e:
        print(f"Edit error: {e}")


async def safe_send_document(
    chat_id: int, file_path: str, caption: str, max_retries: int = 5
):
    for attempt in range(max_retries):
        try:
            if not os.path.exists(file_path):
                print(f"❌ Файл не найден: {file_path}")
                return False

            await bot.send_document(
                chat_id=chat_id,
                document=FSInputFile(file_path),
                caption=caption,
            )
            print(f"✅ Отправлено: {caption[:50]}...")
            return True

        except TelegramRetryAfter as e:
            wait = e.retry_after + 2
            print(
                f"⚠️ Флуд-контроль: ждем {wait}с (попытка {attempt + 1}/{max_retries})"
            )
            await asyncio.sleep(wait)

        except Exception as e:
            error_msg = str(e)
            print(
                f"❌ Ошибка отправки (попытка {attempt + 1}/{max_retries}): {error_msg}"
            )

            if "ClientOSError" in error_msg or "Can not write" in error_msg:
                wait = 15 * (attempt + 1)
                print(f"⏳ Ждем {wait}с перед повтором...")
                await asyncio.sleep(wait)
            elif attempt < max_retries - 1:
                await asyncio.sleep(5)

    print(f"💥 Не удалось отправить после {max_retries} попыток")
    return False


@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    user_id = message.from_user.id if message.from_user else None
    if user_id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав.")
        return
    moscow_tz = pytz.timezone("Europe/Moscow")
    today_key_date = datetime.now(moscow_tz).strftime("%Y%m%d")
    await _reset_counters_for_date(today_key_date)
    await message.answer("✅ Счетчики за сегодня сброшены.")


@dp.message(Command("queue"))
async def cmd_queue(message: Message):
    user_id = message.from_user.id if message.from_user else None
    if user_id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав.")
        return

    queue = get_process_queue()
    current = "Да" if queue.current_task else "Нет"
    await message.answer(
        f"📊 Статус очереди:\n"
        f"📦 В очереди: {queue.get_queue_size()}\n"
        f"🔄 Обрабатывается: {current}"
    )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🤖 Бот для автоматической обработки пачек\n\n"
        "✅ Добавьте бота в любые группы\n"
        "✅ Все файлы обрабатываются последовательно\n"
        "📧 -mails → Google Sheets\n"
        "📋 -logs → sebe/vyaz\n"
        "📤 Остальные → очистка и отправка"
    )


# ==================== обработка ====================


async def _process_mails(message: Message):
    document = message.document
    file_name = document.file_name
    file_size = document.file_size
    chat_title = message.chat.title or "Private"

    size_mb = file_size / (1024 * 1024)
    status_msg = await bot.send_message(
        chat_id=OUTPUT_CHANNEL_TXT_ID,
        text=f"📧 -mails: {file_name}\n📊 {size_mb:.2f} МБ\n⏳ Скачивание...",
    )

    folder = tempfile.mkdtemp(prefix="mails_")
    file_path = os.path.join(folder, file_name)

    try:
        await bot.download(document, destination=file_path)
        await safe_edit(status_msg, "✅ Скачано\n⏳ Распаковка...")

        ext = os.path.splitext(file_name)[1].lower()
        if ext == ".zip":
            with zipfile.ZipFile(file_path, "r") as z:
                if z.testzip():
                    raise RuntimeError("Архив поврежден")
                z.extractall(folder)
        else:
            _extract_rar(file_path, folder)

        await safe_edit(status_msg, "✅ Распаковано\n⏳ Обработка...")

        os.remove(file_path)
        macosx = os.path.join(folder, "__MACOSX")
        if os.path.isdir(macosx):
            shutil.rmtree(macosx, ignore_errors=True)

        all_files = get_all_files_in_archive(folder)
        if not all_files:
            await safe_edit(status_msg, "⚠️ Нет файлов")
            return

        await safe_edit(
            status_msg, f"✅ {len(all_files)} файлов\n⏳ Запись в таблицу..."
        )

        client = init_google_sheets()
        sheet_name = sanitize_sheet_name(chat_title)
        worksheet = get_or_create_sheet(client, GOOGLE_SHEET_URL, sheet_name)
        write_to_sheet(worksheet, file_name, all_files)

        await safe_edit(
            status_msg, f"✅ Готово!\n📦 {file_name}\n📁 {len(all_files)} файлов"
        )

    except Exception as e:
        await safe_edit(status_msg, f"❌ Ошибка: {e}")
        print(f"Mails error: {e}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


async def _process_logs(message: Message):
    document = message.document
    file_name = document.file_name
    file_size = document.file_size
    chat_id = message.chat.id
    chat_title = message.chat.title or "Private"
    chat_tag = choose_tag_for_destination(
        chat_id, chat_title, destination=OUTPUT_CHANNEL_LOGS_ID
    )

    size_mb = file_size / (1024 * 1024)
    status_msg = await bot.send_message(
        chat_id=OUTPUT_CHANNEL_LOGS_ID,
        text=f"📋 -logs: {file_name}\n📊 {size_mb:.2f} МБ\n⏳ Скачивание...",
    )

    folder = tempfile.mkdtemp(prefix="logs_")
    folder_1_5 = tempfile.mkdtemp(prefix="logs_1_5_")
    folder_other = tempfile.mkdtemp(prefix="logs_other_")
    file_path = os.path.join(folder, file_name)

    try:
        await bot.download(document, destination=file_path)
        await safe_edit(status_msg, "✅ Скачано\n⏳ Распаковка...")

        ext = os.path.splitext(file_name)[1].lower()
        if ext == ".zip":
            with zipfile.ZipFile(file_path, "r") as z:
                if z.testzip():
                    raise RuntimeError("Архив поврежден")
                z.extractall(folder)
        else:
            _extract_rar(file_path, folder)

        await safe_edit(status_msg, "✅ Распаковано\n⏳ Сортировка...")

        os.remove(file_path)
        macosx = os.path.join(folder, "__MACOSX")
        if os.path.isdir(macosx):
            shutil.rmtree(macosx, ignore_errors=True)

        subfolders = [
            os.path.join(folder, d)
            for d in os.listdir(folder)
            if os.path.isdir(os.path.join(folder, d))
        ]

        if not subfolders:
            raise RuntimeError("Нет папок в архиве")

        base_folder = subfolders[0]
        for item in os.listdir(base_folder):
            full_path = os.path.join(base_folder, item)
            if os.path.isdir(full_path):
                if "1" in item or "5" in item:
                    shutil.move(full_path, os.path.join(folder_1_5, item))
                else:
                    shutil.move(full_path, os.path.join(folder_other, item))

        await safe_edit(status_msg, "✅ Отсортировано\n⏳ Архивация...")

        archives = []
        if os.listdir(folder_1_5):
            name = await generate_pack_name(chat_id, chat_tag, "sebe")
            out_path = os.path.join(tempfile.gettempdir(), name + ".zip")
            zip_folder(folder_1_5, out_path)
            archives.append((out_path, name))

        if os.listdir(folder_other):
            name = await generate_pack_name(chat_id, chat_tag, "vyaz")
            out_path = os.path.join(tempfile.gettempdir(), name + ".zip")
            zip_folder(folder_other, out_path)
            archives.append((out_path, name))

        if not archives:
            await safe_edit(status_msg, "⚠️ Нет папок для архивации")
            return

        await safe_edit(status_msg, f"✅ {len(archives)} архивов\n⏳ Отправка...")

        for idx, (archive_path, archive_name) in enumerate(archives):
            result_mb = os.path.getsize(archive_path) / (1024 * 1024)
            caption = f"📦 {archive_name}.zip\n🏷️ {chat_title}\n📊 {result_mb:.2f} МБ"

            if idx > 0:
                await asyncio.sleep(5)

            success = await safe_send_document(
                OUTPUT_CHANNEL_LOGS_ID, archive_path, caption
            )

            try:
                os.remove(archive_path)
            except:
                pass

        try:
            await status_msg.delete()
        except:
            pass

    except Exception as e:
        await safe_edit(status_msg, f"❌ Ошибка: {e}")
        print(f"Logs error: {e}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(folder_1_5, ignore_errors=True)
        shutil.rmtree(folder_other, ignore_errors=True)


async def _process_regular(message: Message):
    document = message.document
    file_name = document.file_name
    file_size = document.file_size
    chat_id = message.chat.id
    chat_title = message.chat.title or "Private"
    chat_tag = choose_tag_for_destination(
        chat_id, chat_title, destination=OUTPUT_CHANNEL_TXT_ID
    )

    size_mb = file_size / (1024 * 1024)
    status_msg = await bot.send_message(
        chat_id=OUTPUT_CHANNEL_TXT_ID,
        text=f"📦 {file_name}\n📊 {size_mb:.2f} МБ\n⏳ Скачивание...",
    )

    folder = tempfile.mkdtemp(prefix="pack_")
    file_path = os.path.join(folder, file_name)

    try:
        await bot.download(document, destination=file_path)
        await safe_edit(status_msg, "✅ Скачано\n⏳ Распаковка...")

        if os.path.getsize(file_path) != document.file_size:
            raise RuntimeError("Размер не совпадает")

        ext = os.path.splitext(file_name)[1].lower()
        if ext == ".zip":
            with zipfile.ZipFile(file_path, "r") as z:
                if z.testzip():
                    raise RuntimeError("Архив поврежден")
                z.extractall(folder)
        else:
            base = file_name.lower()
            if any(part in base for part in (".part2", ".part3", ".part4")):
                raise RuntimeError("Загрузите .part1 со всеми частями")
            _extract_rar(file_path, folder)

        await safe_edit(status_msg, "✅ Распаковано\n⏳ Очистка...")

        os.remove(file_path)
        macosx = os.path.join(folder, "__MACOSX")
        if os.path.isdir(macosx):
            shutil.rmtree(macosx, ignore_errors=True)

        try:
            main_cleaner(folder_path=folder)
            await safe_edit(status_msg, "✅ Очищено\n⏳ Архивация...")
        except Exception as e:
            await safe_edit(status_msg, f"⚠️ Ошибка очистки: {e}\n⏳ Архивация...")

        pack_name = await generate_pack_name(chat_id, chat_tag)
        base = os.path.join(folder, pack_name)
        archive_path = shutil.make_archive(base, "zip", folder)

        await safe_edit(status_msg, f"✅ Готово\n⏳ Отправка...")

        moscow_tz = pytz.timezone("Europe/Moscow")
        time_str = datetime.now(moscow_tz).strftime("%H:%M")
        caption = f"📦 {pack_name}.zip\n⏰ {time_str}\n📊 {size_mb:.2f} МБ"

        success = await safe_send_document(OUTPUT_CHANNEL_TXT_ID, archive_path, caption)

        if success:
            try:
                await status_msg.delete()
            except:
                pass
        else:
            await safe_edit(status_msg, "❌ Не удалось отправить")

        try:
            os.remove(archive_path)
        except:
            pass

    except Exception as e:
        await safe_edit(status_msg, f"❌ Ошибка: {e}")
        print(f"Regular error: {e}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


# ==================== фильтры доьавление в очередь ====================


@dp.message(F.document, lambda m: m.document and is_mails_archive(m.document.file_name))
async def handle_mails_archive(message: Message):
    ext = os.path.splitext(message.document.file_name)[1].lower()
    if ext not in (".zip", ".rar"):
        return

    queue = get_process_queue()
    task = ProcessTask(
        task_id=str(message.message_id),
        message=message,
        handler=_process_mails,
        priority=0,
    )
    await queue.add(task)


@dp.message(F.document, lambda m: m.document and is_logs_archive(m.document.file_name))
async def handle_logs_archive(message: Message):
    ext = os.path.splitext(message.document.file_name)[1].lower()
    if ext not in (".zip", ".rar"):
        return

    queue = get_process_queue()
    task = ProcessTask(
        task_id=str(message.message_id),
        message=message,
        handler=_process_logs,
        priority=0,
    )
    await queue.add(task)


@dp.message(
    F.document,
    lambda m: m.document
    and not is_mails_archive(m.document.file_name)
    and not is_logs_archive(m.document.file_name),
)
async def handle_archive(message: Message):
    ext = os.path.splitext(message.document.file_name)[1].lower()
    if ext not in (".zip", ".rar"):
        return

    queue = get_process_queue()
    task = ProcessTask(
        task_id=str(message.message_id),
        message=message,
        handler=_process_regular,
        priority=0,
    )
    await queue.add(task)


async def main():
    queue = init_process_queue(min_delay=3.0)
    await queue.start()

    print(f"🚀 Бот запущен (последовательный режим)")
    print(f"📤 Канал TXT: {OUTPUT_CHANNEL_TXT_ID}")
    print(f"📤 Канал LOGS: {OUTPUT_CHANNEL_LOGS_ID}")

    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await queue.stop()


if __name__ == "__main__":
    asyncio.run(main())
