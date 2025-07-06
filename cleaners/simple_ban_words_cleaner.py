import os
from utils.logger import logger
from database.config import BODIES


def remove_messages_simple(txt_path):
    full_path = f"{txt_path}"

    logger.info(f"start processing: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) > 8:
        lines = lines[8:]

    with open(BODIES, "r", encoding="utf-8") as f:
        ban_words = [line.strip() for line in f if line.strip()]

    output = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("From:"):
            block_lines = [lines[i]]
            i += 1
            while i < len(lines) and not lines[i].startswith("From:"):
                block_lines.append(lines[i])
                if lines[i].startswith("Date:"):
                    break
                i += 1

            snippet_line = next(
                (l for l in block_lines if l.startswith("Snippet:")), ""
            )

            if not any(ban_word in snippet_line for ban_word in ban_words):
                output.extend(block_lines)
        else:
            i += 1

    logger.debug(f"total lines before filter: {len(lines)}")

    cleaned_output = []
    current_block = []

    for line in output:
        if line.startswith("From:") and current_block:
            if cleaned_output:
                cleaned_output.append("\n")
            cleaned_output.extend(current_block)
            current_block = [line]
        else:
            current_block.append(line)

    if current_block:
        if cleaned_output:
            cleaned_output.append("\n")
        cleaned_output.extend(current_block)

    with open(full_path, "w", encoding="utf-8") as f:
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
            remove_messages_simple(full_path)
