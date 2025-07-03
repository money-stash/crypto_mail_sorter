from utils.logger import logger
from database.config import LOGS_FOLDER


def remove_login_attempted_messages(txt_path):
    full_path = f"{LOGS_FOLDER}{txt_path}"

    logger.info(f"start processing: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output = []
    banned_keywords = [
        "Login Attempted",
        "Verification Code",
        "Login Verification",
        "Authorize New Device",
        "Create New API Key",
        "You may apply for your Binance Card now",
        "Verification Successful",
        "Cash Voucher",
        "Cashback Voucher",
        "【Binance】Confirm Your Registration",
        "Claim your NFT",
        "Your new Binance Card has been issued",
        "Your Binance Visa Card is on its way",
        "Claim your 7-day",
        "Bind Google 2FA",
        "You will no longer be able to use your Binance",
    ]

    skip_block = False
    i = 0

    while i < len(lines):
        line = lines[i]
        if line.startswith("Title:") and any(bad in line for bad in banned_keywords):
            i += 2

            while i < len(lines) and lines[i].strip() == "":
                i += 1
            continue

        output.append(line)
        i += 1

    logger.debug(f"total lines before filter: {len(lines)}")

    # очистка от лишних пустых строк
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


remove_login_attempted_messages(
    "" "(66 advance_filter)_(kashif0700444846@gmail.com)_(u0)_SE.txt"
)
