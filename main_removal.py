import os
from utils.logger import logger
from database.config import LOGS_FOLDER, BODIES


def remove_messages(txt_path):
    full_path = f"{txt_path}"

    logger.info(f"start processing: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) > 10:
        if "Emails:" in lines[10]:
            lines = lines[11:]
        elif "Title:" in lines[10]:
            lines = lines[10:]

    with open(BODIES, "r", encoding="utf-8") as f:
        keep_bodies = [line.strip() for line in f if line.strip()]

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

            if any(keep_text in body_line for keep_text in keep_bodies):
                output.extend(block_lines)

        elif line.startswith("Body:"):
            if any(keep_text in line for keep_text in keep_bodies):
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
            remove_messages(full_path)


if __name__ == "__main__":
    process_all_files()
