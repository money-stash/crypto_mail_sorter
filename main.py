import os
import pytz
import zipfile
import shutil
import asyncio
import tempfile
from datetime import datetime
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from database.config import (
    BOT_TOKEN,
    OUTPUT_CHANNEL_LOGS_ID,
    OUTPUT_CHANNEL_TXT_ID,
    GOOGLE_SHEET_URL,
)
from just_cleaner import main_cleaner
from utils.bot_utils import (
    get_all_files_in_archive,
    sanitize_sheet_name,
    init_google_sheets,
    get_or_create_sheet,
    write_to_sheet,
    _extract_rar,
    get_chat_tag,
    zip_folder,
)

LOCAL_API_SERVER = "http://localhost:8081"
local_api = TelegramAPIServer.from_base(LOCAL_API_SERVER, is_local=True)
session = AiohttpSession(api=local_api)
bot = Bot(token=BOT_TOKEN)  # , session=session
dp = Dispatcher(storage=MemoryStorage())

daily_counters = defaultdict(int)


def is_mails_archive(filename: str) -> bool:
    """Проверяет, является ли файл -mails архивом"""
    filename_lower = filename.lower()
    return "-mails" in filename_lower


def is_logs_archive(filename: str) -> bool:
    """Проверяет, является ли файл -logs архивом"""
    filename_lower = filename.lower()
    return "-logs" in filename_lower


def generate_pack_name(chat_id: int, tag: str, suffix: str = "pack") -> str:
    moscow_tz = pytz.timezone("Europe/Moscow")
    now = datetime.now(moscow_tz)
    date_str = now.strftime("%d.%m")
    counter_key = f"{chat_id}-{now.strftime('%Y%m%d')}-{suffix}"
    daily_counters[counter_key] += 1
    pack_number = daily_counters[counter_key]
    return f"{tag}-{pack_number}-{suffix}-{date_str}"


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🤖 Бот для автоматической обработки пачек\n\n"
        "✅ Добавьте бота в любые группы\n"
        "✅ Бот автоматически обработает все архивы\n"
        "📧 -mails архивы → Google Sheets\n"
        "📋 -logs архивы → разделение на sebe/vyaz\n"
        "📤 Остальные → очистка и отправка в канал"
    )


# для -mails архивов
@dp.message(F.document, lambda m: m.document and is_mails_archive(m.document.file_name))
async def handle_mails_archive(message: Message):
    document = message.document
    file_name = document.file_name
    file_size = document.file_size

    ext = os.path.splitext(file_name)[1].lower()
    if ext not in (".zip", ".rar"):
        return

    chat_title = message.chat.title or "Private"

    size_mb = file_size / (1024 * 1024)
    status_msg = await bot.send_message(
        chat_id=OUTPUT_CHANNEL_TXT_ID,
        text=(
            f"📧 Обработка -mails архива\n"
            f"📦 {file_name}\n"
            f"📊 {size_mb:.2f} МБ\n"
            f"⏳ Скачивание..."
        ),
    )

    folder = tempfile.mkdtemp(prefix="mails_")
    file_path = os.path.join(folder, file_name)

    try:
        await bot.download(document, destination=file_path)
        await status_msg.edit_text(f"✅ Скачано\n⏳ Распаковка...")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка скачивания: {e}")
        shutil.rmtree(folder, ignore_errors=True)
        return

    try:
        if ext == ".zip":
            with zipfile.ZipFile(file_path, "r") as z:
                bad = z.testzip()
                if bad:
                    raise RuntimeError(f"Поврежден: {bad}")
                z.extractall(folder)
        else:
            _extract_rar(file_path, folder)

        await status_msg.edit_text("✅ Распаковано\n⏳ Сканирование файлов...")

        try:
            os.remove(file_path)
        except:
            pass

        macosx_dir = os.path.join(folder, "__MACOSX")
        if os.path.isdir(macosx_dir):
            shutil.rmtree(macosx_dir, ignore_errors=True)

        all_files = get_all_files_in_archive(folder)

        if not all_files:
            await status_msg.edit_text("⚠️ В архиве не найдено файлов")
            return

        await status_msg.edit_text(
            f"✅ Найдено файлов: {len(all_files)}\n⏳ Запись в Google Таблицу..."
        )

        try:
            client = init_google_sheets()
            sheet_name = sanitize_sheet_name(chat_title)
            worksheet = get_or_create_sheet(client, GOOGLE_SHEET_URL, sheet_name)
            write_to_sheet(worksheet, file_name, all_files)

            await status_msg.edit_text(
                f"✅ Готово!\n"
                f"📦 Архив: {file_name}\n"
                f"📁 Файлов: {len(all_files)}\n"
                f"📊 Записано в лист: {sheet_name}"
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ Ошибка записи в таблицу: {e}")
            print(f"Google Sheets error: {e}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка обработки: {e}")
        print(f"Processing error: {e}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


# для -logs архивов (разделение на sebe и vyaz)
@dp.message(F.document, lambda m: m.document and is_logs_archive(m.document.file_name))
async def handle_logs_archive(message: Message):
    document = message.document
    file_name = document.file_name
    file_size = document.file_size

    ext = os.path.splitext(file_name)[1].lower()
    if ext not in (".zip", ".rar"):
        return

    chat_id = message.chat.id
    chat_title = message.chat.title or "Private"
    chat_tag = get_chat_tag(chat_id, chat_title)

    folder = tempfile.mkdtemp(prefix="logs_")
    folder_1_5 = tempfile.mkdtemp(prefix="logs_1_5_")
    folder_other = tempfile.mkdtemp(prefix="logs_other_")
    file_path = os.path.join(folder, file_name)

    size_mb = file_size / (1024 * 1024)
    status_msg = await bot.send_message(
        chat_id=OUTPUT_CHANNEL_LOGS_ID,
        text=(
            f"📋 Обработка -logs архива\n"
            f"📦 {file_name}\n"
            f"📊 {size_mb:.2f} МБ\n"
            f"⏳ Скачивание..."
        ),
    )

    try:
        await bot.download(document, destination=file_path)
        await status_msg.edit_text("✅ Скачано\n⏳ Распаковка...")

        if ext == ".zip":
            with zipfile.ZipFile(file_path, "r") as z:
                bad = z.testzip()
                if bad:
                    raise RuntimeError(f"Поврежден: {bad}")
                z.extractall(folder)
        else:
            _extract_rar(file_path, folder)

        await status_msg.edit_text("✅ Распаковано\n⏳ Сортировка файлов...")

        try:
            os.remove(file_path)
        except:
            pass

        macosx_dir = os.path.join(folder, "__MACOSX")
        if os.path.isdir(macosx_dir):
            shutil.rmtree(macosx_dir, ignore_errors=True)

        subfolders = [
            os.path.join(folder, d)
            for d in os.listdir(folder)
            if os.path.isdir(os.path.join(folder, d))
        ]

        if not subfolders:
            raise RuntimeError("В архиве нет папок")

        base_folder = subfolders[0]

        for item in os.listdir(base_folder):
            full_path = os.path.join(base_folder, item)
            if os.path.isdir(full_path):
                if "1" in item or "5" in item:
                    shutil.move(full_path, os.path.join(folder_1_5, item))
                else:
                    shutil.move(full_path, os.path.join(folder_other, item))

        await status_msg.edit_text("✅ Отсортировано\n⏳ Создание архивов...")

        archives = []

        if os.listdir(folder_1_5):
            name = generate_pack_name(chat_id, chat_tag, "sebe")
            out_path = os.path.join(tempfile.gettempdir(), name + ".zip")
            zip_folder(folder_1_5, out_path)
            archives.append((out_path, name))

        if os.listdir(folder_other):
            name = generate_pack_name(chat_id, chat_tag, "vyaz")
            out_path = os.path.join(tempfile.gettempdir(), name + ".zip")
            zip_folder(folder_other, out_path)
            archives.append((out_path, name))
            arch_list = "\n".join([f"✅ Архив упакован: {a[1]}.zip" for a in archives])

        if not archives:
            await status_msg.edit_text("⚠️ Нет папок для архивации")
            return

        await status_msg.edit_text(
            f"✅ Создано архивов: {len(archives)}\n⏳ Отправка..."
        )

        for archive_path, archive_name in archives:
            result_size = os.path.getsize(archive_path)
            result_mb = result_size / (1024 * 1024)

            caption = (
                f"📦 {archive_name}.zip\n"
                f"🏷️ Чат: {chat_title}\n"
                f"📊 {result_mb:.2f} МБ"
            )

            try:
                await bot.send_document(
                    chat_id=OUTPUT_CHANNEL_LOGS_ID,
                    document=FSInputFile(archive_path),
                    caption=caption,
                )
                sent_list = "\n".join(
                    [
                        f"📤 Архив отправлен: {a[1]}.zip"
                        for a in archives[
                            : archives.index((archive_path, archive_name)) + 1
                        ]
                    ]
                )
            except Exception as e:
                await status_msg.edit_text(f"❌ Ошибка отправки: {e}")
                print(f"Send error: {e}")
            finally:
                try:
                    os.remove(archive_path)
                except:
                    pass

        try:
            await status_msg.delete()
        except:
            pass

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")
        print(f"Logs processing error: {e}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(folder_1_5, ignore_errors=True)
        shutil.rmtree(folder_other, ignore_errors=True)


# для обычных архивов (игнорируем -mails и -logs)
@dp.message(
    F.document,
    lambda m: m.document
    and not is_mails_archive(m.document.file_name)
    and not is_logs_archive(m.document.file_name),
)
async def handle_archive(message: Message):
    document = message.document
    file_name = document.file_name
    file_size = document.file_size

    ext = os.path.splitext(file_name)[1].lower()
    if ext not in (".zip", ".rar"):
        return

    chat_id = message.chat.id
    chat_title = message.chat.title or "Private"
    chat_tag = get_chat_tag(chat_id, chat_title)

    size_mb = file_size / (1024 * 1024)
    status_msg = await bot.send_message(
        chat_id=OUTPUT_CHANNEL_TXT_ID,
        text=(f"📦 Обработка\n" f"📊 {size_mb:.2f} МБ\n" f"⏳ Скачивание..."),
    )

    folder = tempfile.mkdtemp(prefix="pack_")
    file_path = os.path.join(folder, file_name)

    try:
        await bot.download(document, destination=file_path)
        await status_msg.edit_text(f"✅ Скачано\n⏳ Распаковка...")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")
        shutil.rmtree(folder, ignore_errors=True)
        return

    try:
        if os.path.getsize(file_path) != document.file_size:
            raise RuntimeError("Размер не совпадает")

        if ext == ".zip":
            with zipfile.ZipFile(file_path, "r") as z:
                bad = z.testzip()
                if bad:
                    raise RuntimeError(f"Поврежден: {bad}")
                z.extractall(folder)
        else:
            base = file_name.lower()
            if any(part in base for part in (".part2", ".part3", ".part4")):
                raise RuntimeError("Загрузите .part1 со всеми частями")
            _extract_rar(file_path, folder)

        await status_msg.edit_text("✅ Распаковано\n⏳ Очистка...")

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка распаковки: {e}")
        shutil.rmtree(folder, ignore_errors=True)
        return

    try:
        os.remove(file_path)
    except:
        pass

    macosx_dir = os.path.join(folder, "__MACOSX")
    if os.path.isdir(macosx_dir):
        shutil.rmtree(macosx_dir, ignore_errors=True)

    archive_path = None
    try:
        try:
            main_cleaner(folder_path=folder)
            await status_msg.edit_text("✅ Очищено\n⏳ Архивация...")
        except Exception as e:
            await status_msg.edit_text(f"⚠️ Ошибка очистки: {e}\n⏳ Архивация...")

        pack_name = generate_pack_name(chat_id, chat_tag)

        base = os.path.join(folder, pack_name)
        archive_path = shutil.make_archive(base, "zip", folder)

        # Use the original size_mb calculated from the file_size
        await status_msg.edit_text(f"✅ Готово ({size_mb:.2f} МБ)\n📤 Отправка...")

        moscow_tz = pytz.timezone("Europe/Moscow")
        now = datetime.now(moscow_tz)
        time_str = now.strftime("%H:%M")

        caption = (
            f"📦 {pack_name}.zip\n"
            f"⏰ Время сдачи: {time_str}\n"
            f"📊 {size_mb:.2f} МБ"
        )

        try:
            await bot.send_document(
                chat_id=OUTPUT_CHANNEL_TXT_ID,
                document=FSInputFile(archive_path),
                caption=caption,
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ Ошибка отправки в канал: {e}")
            print(f"Send error: {e}")
        else:
            try:
                await status_msg.delete()
            except:
                pass

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")
        print(f"Error: {e}")
    finally:
        if archive_path and os.path.exists(archive_path):
            try:
                os.remove(archive_path)
            except:
                pass
        shutil.rmtree(folder, ignore_errors=True)


async def main():
    print(f"🚀 Бот запущен")
    print(f"📊 Макс размер: 2000 МБ")
    print(f"📤 Канал: {OUTPUT_CHANNEL_TXT_ID}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
