import os
import re
import shutil
import subprocess

from database.config import GOOGLE_CREDENTIALS_FILE, CHAT_TAGS

import gspread
from google.oauth2.service_account import Credentials


def init_google_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE, scopes=scopes
    )
    client = gspread.authorize(creds)
    return client


def get_or_create_sheet(client, spreadsheet_url, sheet_name):
    spreadsheet = client.open_by_url(spreadsheet_url)

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        print(f"📄 Найден существующий лист: {sheet_name}")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
        print(f"📄 Создан новый лист: {sheet_name}")

    return worksheet


def write_to_sheet(worksheet, archive_name, file_list):
    all_values = worksheet.get_all_values()
    start_row = len(all_values) + 1

    if start_row == 1:
        worksheet.update("A1:B1", [["Архив", "Файлы"]])
        start_row = 2

    num_files = len(file_list)

    worksheet.update_cell(start_row, 1, archive_name)

    for i, file_name in enumerate(file_list):
        worksheet.update_cell(start_row + i, 2, file_name)

    if num_files > 1:
        end_row = start_row + num_files - 1
        worksheet.merge_cells(f"A{start_row}:A{end_row}", merge_type="MERGE_ALL")
        print(f"🔗 Объединены ячейки A{start_row}:A{end_row}")


def _which(*tools):
    for t in tools:
        p = shutil.which(t)
        if p:
            return p
    return None


def _pick_7z():
    candidates = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return _which("7z", "7zz", "7zzs")


def _extract_rar(file_path: str, out_dir: str):
    tool = _which("unar") or _pick_7z() or _which("unrar")
    if not tool:
        raise RuntimeError("No RAR extractor found. Install unar or 7zip or unrar.")
    name = os.path.basename(tool).lower()
    if "unar" in name:
        r = subprocess.run(
            [tool, "-force-overwrite", "-quiet", "-o", out_dir, file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    elif "7z" in name or "7zz" in name:
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


def should_process_file(filename: str) -> bool:
    filename_lower = filename.lower()
    return "-mails" in filename_lower


def get_all_files_in_archive(folder_path: str) -> list:
    all_files = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            all_files.append(file)

    return sorted(all_files)


def sanitize_sheet_name(name: str) -> str:
    name = re.sub(r"[:\\/\?\*\[\]]", "", name)

    return name[:100] if name else "Unknown"


def get_chat_tag(chat_id: int, chat_title: str) -> str:
    if chat_id in CHAT_TAGS:
        return CHAT_TAGS[chat_id]
    tag = re.sub(r"[^a-zA-Z0-9а-яА-Я]", "", chat_title)
    return tag[:10] if tag else "pack"


def zip_folder(folder_path: str, output_path: str):
    shutil.make_archive(output_path.replace(".zip", ""), "zip", folder_path)
