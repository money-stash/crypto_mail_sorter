import os
import chardet
from utils.logger import logger
from config import BODIES


def detect_encoding(file_path):
    """Определяет кодировку файла"""
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
            return detected["encoding"] or "utf-8"
    except:
        return "utf-8"


def remove_messages_paranoid(txt_path):
    full_path = f"{txt_path}"

    logger.info(f"start processing: {full_path}")

    encoding = detect_encoding(full_path)

    with open(full_path, "r", encoding=encoding, errors="replace") as f:
        lines = f.readlines()

    if len(lines) > 10:
        if "Emails:" in lines[10]:
            lines = lines[11:]
        elif "Title:" in lines[10]:
            lines = lines[10:]

    ban_encoding = detect_encoding(BODIES)
    with open(BODIES, "r", encoding=ban_encoding, errors="replace") as f:
        ban_words = [line.strip() for line in f if line.strip()]

    output = []

    i = 0

    while i < len(lines):
        line = lines[i]
        if line.startswith("Title:"):
            block_lines = [line]
            i += 1

            while i < len(lines) and not lines[i].startswith("Title:"):
                block_lines.append(lines[i])
                i += 1

            body_line = next((l for l in block_lines if l.startswith("Body:")), "")
            body_content = body_line.strip()[5:].strip()

            if body_content and not any(
                ban_word in body_line for ban_word in ban_words
            ):
                output.extend(block_lines)

        elif line.startswith("Body:"):
            if not any(ban_word in line for ban_word in ban_words):
                output.append(line)
            i += 1

        else:
            output.append(line)
            i += 1

    logger.debug(f"total lines before filter: {len(lines)}")

    cleaned_output = []
    empty = False
    for line in output:
        if line.strip() == "":
            if not empty:
                cleaned_output.append("\n")
            empty = True
        else:
            cleaned_output.append(line)
            empty = False

    with open(full_path, "w", encoding=encoding, errors="replace") as f:
        f.writelines(cleaned_output)
        logger.info(f"saved cleaned file: {full_path}")
        logger.info(f"total lines after cleanup: {len(cleaned_output)}")
        logger.info("removal complete")

    if len(cleaned_output) == 0:
        os.remove(full_path)
        logger.info(f"deleted empty file: {full_path}")


def process_all_files():
    folder_path = "dirty_logs/"
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            full_path = os.path.join(folder_path, filename)
            remove_messages_paranoid(full_path)
