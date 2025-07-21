import re, time, json, random
from pathlib import Path
from utils.logger import logger
from utils.pollinations_utils import ask_ai_with_fallback
from utils.file_utils import (
    add_ban_word,
    remove_messages_by_snippet_match_simple,
    remove_messages_by_snippet_match_paranoid,
)

from database.config import WITHDRAW_REG, P2P_REG, DEPOSIT_REG, BODIES


def extract_transaction_info(text: str):
    """ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ О ТРАНЗЕ ИЛИ ДОБАВЛЕНИЯ НОВОГО БАН СЛОВА"""
    try:
        with open(WITHDRAW_REG, "r", encoding="utf-8") as f:
            withdrawal_patterns = [line.strip() for line in f if line.strip()]
    except Exception:
        withdrawal_patterns = []

    for pattern in withdrawal_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(",", ""))
            currency = match.group(2)
            return amount, currency, "withdrawal"

    try:
        with open(DEPOSIT_REG, "r", encoding="utf-8") as f:
            deposit_patterns = [line.strip() for line in f if line.strip()]
    except Exception:
        deposit_patterns = []

    for pattern in deposit_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(",", ""))
            currency = match.group(2)
            return amount, currency, "deposit"

    try:
        with open(P2P_REG, "r", encoding="utf-8") as f:
            p2p_patterns = [line.strip() for line in f if line.strip()]
    except Exception:
        p2p_patterns = []

    for pattern in p2p_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(",", ""))
            currency = match.group(2)
            return amount, currency, "p2p"

    if "p2p" in text.lower():
        return False

    try:
        ai_answer = ask_ai_with_fallback(
            f"""Это сообщение может быть на любом языке. 
Если оно ЯВНО связано с транзакцией (депозит, вывод, перевод) — это НЕ мусор. 
Если нет — это мусор (trash).

⚠️ Игнорируй купоны, бонусы, акции, новости и т.п., даже если там есть суммы или крипта. 
Считай только операции с деньгами. 
Если это мусор — верни JSON: {{reg: короткий маркер из текста, type: trash}}.

Сообщение:
{text}
"""
        )
        print(ai_answer)

        fixed_json = re.sub(r"([{,]\s*)(\w+)(\s*:\s*)", r'\1"\2"\3', ai_answer)
        fixed_json = re.sub(r":\s*([a-zA-Z_]+)([,\}])", r': "\1"\2', fixed_json)

        match = re.search(r'\{.*?"type":\s*".+?".*?\}', fixed_json, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if parsed["type"] == "trash":
                    cleaned = re.split(r"\\?\([^)]+\\?\)", parsed["reg"])[0].strip()
                    parsed["reg"] = cleaned
                return {"type": parsed["type"], "reg": parsed["reg"]}
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode failed: {e}")
                raise ValueError("Invalid JSON after fixing formatting")
        else:
            raise ValueError("No valid JSON found in AI response")

    except Exception as ex:
        logger.error(f"WHILE ASK AI: {ex}")
        return False


def process_withdrawals_from_file(file_path: str, checker_name: str):
    with open(file_path, "r", encoding="utf-8") as f:
        # чистим ещё раз файл
        res_for_ai = []
        for line in f:
            if line.startswith("Body: "):
                text = line[len("Body: ") :].strip()
                result = extract_transaction_info(text)

                if result:
                    if isinstance(result, dict) and result["type"] == "trash":
                        with open(BODIES, "r", encoding="utf-8") as booi:
                            boodies_lines = [
                                line.strip() for line in booi if line.strip()
                            ]
                        if not any(
                            result["reg"].strip() in line.strip()
                            for line in boodies_lines
                        ):
                            remove_messages_by_snippet_match_paranoid(
                                file_path, target_snippet=[result["reg"]]
                            )
                            logger.info(f"УДАЛИЛ: {result['reg']}")
                            add_ban_word(result["reg"])
                            time.sleep(random.randint(5, 15))
                            continue

                    print("------------")
                    print(text)
                    # logger.info(f"ДОБАВИЛ ТРАНЗУ: {result}")
                    print("------------")
                    res_for_ai.append(result)

            elif line.startswith("Snippet: "):
                text = line[len("Snippet: ") :].strip()
                result = extract_transaction_info(text)

                if result:
                    if isinstance(result, dict) and result["type"] == "trash":
                        with open(BODIES, "r", encoding="utf-8") as booi:
                            boodies_lines = [
                                line.strip() for line in booi if line.strip()
                            ]
                        if not any(
                            result["reg"].strip() in line.strip()
                            for line in boodies_lines
                        ):
                            remove_messages_by_snippet_match_simple(
                                file_path, target_snippet=[result["reg"]]
                            )
                            logger.info(f"УДАЛИЛ: {result['reg']}")
                            add_ban_word(result["reg"])
                            time.sleep(random.randint(5, 15))
                            continue

                    print("------------")
                    print(text)
                    logger.info(f"ДОБАВИЛ ТРАНЗУ: {result}")
                    print("------------")
                    res_for_ai.append(result)

        # пред угадываем балик
        if len(res_for_ai) > 5:
            ai_answer = ask_ai_with_fallback(
                text=f"Проанализируй вот эти данные с криптобиржи человека, и постарайся предугадать примерный баланс в. Не считай транзакции, они могут быть только на вывод, прирное число баланса $(ВОЗВРАЩАЙ ТОЛЬКО ЧИСЛО В ДОЛЛАРАХ, БОЛЬШЕ, НИЧЕГО НЕ ПИШИ!):\n\n{res_for_ai}"
            )
            logger.info(ai_answer)

            return ai_answer


# file_balance = process_withdrawals_from_file(
#     "dirty_logs/1452_do_not_reply@ses_binance_com_tadas_svaikevicius@ozogimnazija.txt",
#     "paranoid",
# )
# print(f"FILE BALANCE: {file_balance}")
