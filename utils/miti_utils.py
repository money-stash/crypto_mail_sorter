from datetime import datetime
import json
import asyncio
from pathlib import Path

import pytz
from config import (
    SUPPLIERS,
    OUTPUT_CHANNEL_LOGS_ID,
    OUTPUT_CHANNEL_TXT_ID,
    COUNTERS_DIR,
    _counters_lock,
)


def choose_tag_for_destination(
    chat_id: int, chat_title: str, destination: int | None = None
) -> str:
    supplier = SUPPLIERS.get(chat_id)
    title = chat_title or "Private"
    if not supplier:
        return title
    if destination in (OUTPUT_CHANNEL_TXT_ID, OUTPUT_CHANNEL_LOGS_ID):
        return supplier.get("alias") or supplier.get("real") or title
    return supplier.get("real") or supplier.get("alias") or title


def _counters_file_for_date(date_str: str) -> Path:
    return COUNTERS_DIR / f"counters-{date_str}.json"


async def _load_counters_for_date(date_str: str) -> dict:
    file_path = _counters_file_for_date(date_str)
    if not file_path.exists():
        return {}
    async with _counters_lock:
        return await asyncio.to_thread(
            lambda: json.loads(file_path.read_text(encoding="utf-8") or "{}")
        )


async def _save_counters_for_date(date_str: str, data: dict) -> None:
    file_path = _counters_file_for_date(date_str)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    async with _counters_lock:
        await asyncio.to_thread(
            lambda: file_path.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
        )


async def _increment_counter_key(date_str: str, key: str) -> int:
    counters = await _load_counters_for_date(date_str)
    value = int(counters.get(key, 0)) + 1
    counters[key] = value
    await _save_counters_for_date(date_str, counters)
    return value


async def _reset_counters_for_date(date_str: str) -> None:
    await _save_counters_for_date(date_str, {})


async def generate_pack_name(chat_id: int, tag: str, suffix: str = "pack") -> str:
    moscow_tz = pytz.timezone("Europe/Moscow")
    now = datetime.now(moscow_tz)
    date_str = now.strftime("%d.%m")
    key_date = now.strftime("%Y%m%d")
    counter_key = f"{chat_id}-{key_date}-{suffix}"
    pack_number = await _increment_counter_key(key_date, counter_key)
    return f"{tag}-{pack_number}-{suffix}-{date_str}"
