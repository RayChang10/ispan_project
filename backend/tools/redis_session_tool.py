#!/usr/bin/env python3
"""
Redis Session Tools

用途：
- 以 user_id 區分，將面試歷程的事件與狀態寫入 Redis，供 LLM 即時作為「記憶」。
- 提供查詢與清空工具，方便流程控制與測試。

環境變數：
- REDIS_URL (default: redis://localhost:6379/0)
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.session_store import (
    append_event as redis_append_event,
    list_events as redis_list_events,
    set_state as redis_set_state,
    get_state as redis_get_state,
    clear_session as redis_clear_session,
)


def save_interview_event(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """將事件寫入 Redis（右推），成功回傳 status=success。"""
    redis_append_event(user_id, event)
    return {"status": "success", "message": "event_saved"}


def save_interview_state(user_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """更新會話狀態（以 JSON 形式存於 hash）。"""
    redis_set_state(user_id, state)
    return {"status": "success", "message": "state_saved"}


def get_interview_state(user_id: str) -> Dict[str, Any]:
    """讀取最新狀態（若無則回傳空 dict）。"""
    state = redis_get_state(user_id)
    return {"status": "success", "data": state}


def list_interview_events(user_id: str) -> Dict[str, Any]:
    """讀取所有事件（List，時間順序）。"""
    events = redis_list_events(user_id)
    return {"status": "success", "data": events}


def clear_interview_session(user_id: str) -> Dict[str, Any]:
    """清除該使用者的所有事件與狀態。"""
    redis_clear_session(user_id)
    return {"status": "success", "message": "session_cleared"}


__all__ = [
    "save_interview_event",
    "save_interview_state",
    "get_interview_state",
    "list_interview_events",
    "clear_interview_session",
]


