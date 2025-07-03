from utils.logger import logger
from database.config import LOGS_FOLDER, BODIES


def remove_kucoin_messages(txt_path):
    full_path = f"{LOGS_FOLDER}{txt_path}"

    logger.info(f"start processing: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    if (
        len(lines) >= 8
        and lines[0].strip() == "Telegram: https://t.me/paranoid_checker"
        and lines[1].strip() == "Support: https://t.me/Checker_Support"
        and lines[2].strip() == "Support Bot: https://t.me/Checker_Support_Bot"
        and lines[3].strip() == ""
        and lines[4].strip() == "Gmail:"
        and lines[5].strip().startswith("Email:")
        and lines[6].strip().startswith("Address:")
        and lines[7].strip().startswith("Index:")
    ):
        lines = lines[8:]

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


remove_kucoin_messages("Gmail_Info.txt")
