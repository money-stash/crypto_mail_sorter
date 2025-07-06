import re, time, json
from pathlib import Path
from utils.logger import logger
from utils.pollinations_utils import ask_ai
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
        ai_answer = ask_ai(
            f"""Проанализируй полностью вот это сообщение. 
    Если в нём ЯВНО УКАЗАНЫ сумма и валюта или криптовалюта (например: 120 USDT, 0.005 BTC, 90000 SHIB), 
    верни JSON-объект в формате: {{reg: регулярка, type: тип}}, 
    где reg — регулярка с двумя группами (сумма и валюта), 
    а type — один из: deposit, withdraw, p2p.

    ЕСЛИ В СООБЩЕНИИ НЕ НАПИСАНА КРИПТА ИЛИ ВАЛЮТА — это мусор. 
    В таком случае верни JSON в формате: {{reg: текст из сообщения, по которому можно будет в будущем понять, что оно мусорное, type: trash}}. 
    НЕ ВОЗВРАЩАЙ РЕГУЛЯРКУ ДЛЯ МУСОРА, ТОЛЬКО ХАРАКТЕРНУЮ ФРАЗУ ИЗ ТЕКСТА.

    Сообщение:
    {text}
    """
        )
        match = re.search(r'\{.*?"type":\s*".+?".*?\}', ai_answer, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            return {"type": parsed["type"], "reg": parsed["reg"]}
        else:
            raise ValueError("No valid JSON found in AI response")

    except Exception as ex:
        logger.error(f"WHILE ASK AI: {ex}")
        return False


def process_withdrawals_from_file(file_path: str, checker_name: str):
    with open(file_path, "r", encoding="utf-8") as f:
        # чистим ещё раз файл
        with open(BODIES, "r", encoding="utf-8") as booi:
            boodies_lines = booi.readlines()
            if checker_name == "simple":
                remove_messages_by_snippet_match_simple(file_path, boodies_lines)
            else:
                remove_messages_by_snippet_match_paranoid(file_path, boodies_lines)

        res_for_ai = []
        for line in f:
            if line.startswith("Body: "):
                text = line[len("Body: ") :].strip()
                result = extract_transaction_info(text)

                if result:
                    # если вернуло словарь - отвечала нейронка
                    if isinstance(result, dict):
                        if result["type"] == "trash":
                            remove_messages_by_snippet_match_paranoid(
                                file_path, target_snippet=[result["reg"]]
                            )
                            print(f"УДАЛИЛИ: {result['reg']}")
                            add_ban_word(result["reg"])
                            time.sleep(10)
                            return

                    res_for_ai.append(result)

            elif line.startswith("Snippet: "):
                text = line[len("Snippet: ") :].strip()
                result = extract_transaction_info(text)

                if result:
                    if isinstance(result, dict):
                        if result["type"] == "trash":
                            remove_messages_by_snippet_match_simple(
                                file_path, target_snippet=[result["reg"]]
                            )
                            print(f"УДАЛИЛИ: {result['reg']}")
                            add_ban_word(result["reg"])
                            time.sleep(10)
                            return

                    res_for_ai.append(result)

        # пред угадываем балик
        if len(res_for_ai) > 5:
            ai_answer = ask_ai(
                text=f"Проанализируй вот эти данные с криптобиржи человека, и постарайся предугадать примерный баланс в $(ВОЗВРАЩАЙ ТОЛЬКО ЧИСЛО В ДОЛЛАРАХ, БОЛЬШЕ, НИЧЕГО НЕ ПИШИ!):\n\n{res_for_ai}"
            )
            print(ai_answer)
            parsed = json.loads(ai_answer)
            print(parsed["type"])
            time.sleep(100)


process_withdrawals_from_file(
    "dirty_logs/(100 advance_filter)_(dungtrananh39@gmail.com)_(u0)_VN.txt",
    "paranoid",
)
