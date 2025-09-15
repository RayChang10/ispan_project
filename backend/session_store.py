#!/usr/bin/env python3
"""
Redis 會話儲存：
- 以 user_id 分群組，將面試歷程逐步寫入 Redis，供 LLM 即時取用作為「記憶」。
- 面試完成時可一次取出，轉存至關聯式資料庫。

Key 命名：
- session:{user_id}:events     -> list (按時間 push)
- session:{user_id}:state      -> hash（目前階段、最近問題等）

環境變數：
- REDIS_URL (default: redis://localhost:6379/0)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import redis


def _get_client() -> redis.Redis:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url, decode_responses=True)


def _key_events(user_id: str) -> str:
    # 使用 conversation 命名空間儲存對話紀錄，更具描述性
    return f"conversation:{user_id}:events"


def _key_state(user_id: str) -> str:
    # 使用 conversation 命名空間儲存會話狀態
    return f"conversation:{user_id}:state"


def append_event(user_id: str, event: Dict[str, Any]) -> None:
    client = _get_client()
    client.rpush(_key_events(user_id), json.dumps(event, ensure_ascii=False))


def set_state(user_id: str, state: Dict[str, Any]) -> None:
    client = _get_client()
    # 以整個 JSON 存放，避免欄位爆炸
    client.hset(_key_state(user_id), mapping={"json": json.dumps(state, ensure_ascii=False)})


def get_state(user_id: str) -> Dict[str, Any]:
    client = _get_client()
    raw = client.hget(_key_state(user_id), "json")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def list_events(user_id: str, start: int = 0, end: int = -1) -> List[Dict[str, Any]]:
    client = _get_client()
    raw_list = client.lrange(_key_events(user_id), start, end)
    events: List[Dict[str, Any]] = []
    for raw in raw_list:
        try:
            events.append(json.loads(raw))
        except Exception:
            continue
    return events


def clear_session(user_id: str) -> None:
    client = _get_client()
    client.delete(_key_events(user_id))
    client.delete(_key_state(user_id))


