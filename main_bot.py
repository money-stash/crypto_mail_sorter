import os
import uuid
import zipfile
import rarfile
import shutil
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from database.config import BOT_TOKEN
from just_cleaner import main_cleaner

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Send me a .zip or .rar archive.")


@dp.message(F.document)
async def handle_archive(message: Message):
    document = message.document
    file_name = document.file_name
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in (".zip", ".rar"):
        await message.answer("Unsupported file type.")
        return
    folder = str(uuid.uuid4())
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, file_name)
    await bot.download(document, destination=file_path)
    try:
        if ext == ".zip":
            with zipfile.ZipFile(file_path, "r") as archive:
                archive.extractall(folder)
        else:
            with rarfile.RarFile(file_path, "r") as archive:
                archive.extractall(folder)
    except Exception as e:
        await message.answer(f"Extraction failed: {e}")
        shutil.rmtree(folder)
        return
    os.remove(file_path)
    macosx_dir = os.path.join(folder, "__MACOSX")
    if os.path.isdir(macosx_dir):
        shutil.rmtree(macosx_dir)

    await message.answer("Archive extracted successfully. Starting cleaning process...")

    main_cleaner(folder_path=folder)
    archive_path = shutil.make_archive(folder, "zip", folder)

    await message.reply_document(FSInputFile(archive_path))

    os.remove(archive_path)
    shutil.rmtree(folder)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
