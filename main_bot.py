import os
import uuid
import zipfile
import shutil
import asyncio
import tempfile
import subprocess

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from database.config import BOT_TOKEN
from just_cleaner import main_cleaner

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def _which(*tools):
    for t in tools:
        p = shutil.which(t)
        if p:
            return p
    return None


def _extract_rar(file_path: str, out_dir: str):
    tool = _which("unar") or _which("7z", "7zz", "7zzs") or _which("unrar")
    if not tool:
        raise RuntimeError("No RAR extractor found. Install unar or 7zip or unrar.")
    if os.path.basename(tool).lower().startswith("unar"):
        r = subprocess.run(
            [tool, "-force-overwrite", "-quiet", "-o", out_dir, file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    elif os.path.basename(tool).lower().startswith(("7z", "7zz")):
        r = subprocess.run(
            [tool, "x", "-y", f"-o{out_dir}", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        r = subprocess.run(
            [tool, "x", "-o+", file_path, out_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    if r.returncode != 0:
        msg = r.stderr.decode(errors="ignore") or r.stdout.decode(errors="ignore")
        raise RuntimeError(msg.strip() or "RAR extraction failed")


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

    folder = tempfile.mkdtemp(prefix="extract_")
    file_path = os.path.join(folder, file_name)
    await bot.download(document, destination=file_path)

    try:
        if os.path.getsize(file_path) != document.file_size:
            raise RuntimeError("Downloaded file size mismatch")

        if ext == ".zip":
            with zipfile.ZipFile(file_path, "r") as z:
                bad = z.testzip()
                if bad:
                    raise RuntimeError(f"Corrupted entry: {bad}")
                z.extractall(folder)
        else:
            base = file_name.lower()
            if any(part in base for part in (".part2", ".part3", ".part4")):
                raise RuntimeError("Multipart RAR: upload .part1 and all parts")
            _extract_rar(file_path, folder)
    except Exception as e:
        await message.answer(f"Extraction failed: {e}")
        shutil.rmtree(folder, ignore_errors=True)
        return

    try:
        os.remove(file_path)
    except Exception:
        pass

    macosx_dir = os.path.join(folder, "__MACOSX")
    if os.path.isdir(macosx_dir):
        shutil.rmtree(macosx_dir, ignore_errors=True)

    await message.answer("Archive extracted successfully. Starting cleaning process...")

    try:
        main_cleaner(folder_path=folder)
    except Exception as e:
        await message.answer(f"Cleaner error: {e}")

    archive_path = shutil.make_archive(folder, "zip", folder)

    await message.reply_document(FSInputFile(archive_path))

    try:
        os.remove(archive_path)
    except Exception:
        pass
    shutil.rmtree(folder, ignore_errors=True)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
