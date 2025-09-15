#!/usr/bin/env python3
"""
PostgreSQL Interview Persist Tools

用途：
- 將 Redis 收集到的面試歷程事件，批次（或單筆）落盤到關聯式資料庫。
- 透過 SQLAlchemy 的 `InterviewSession` 模型存成逐筆記錄。

需求：
- 已設定環境變數 `DATABASE_URL` 指向 PostgreSQL（例如 compose 已設）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from backend.db_sa import InterviewSession, SessionLocal


def _user_id_to_int_or_none(user_id: str) -> int | None:
    return int(user_id) if str(user_id).isdigit() else None


def persist_event_to_db(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """將單一事件寫入 InterviewSession。

    回傳：{"status": "success", "rows": 1}
    """
    session = SessionLocal()
    try:
        row = InterviewSession(
            user_id=_user_id_to_int_or_none(user_id),
            session_data=json.dumps(event, ensure_ascii=False),
        )
        session.add(row)
        session.commit()
        return {"status": "success", "rows": 1}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


def persist_events_to_db(user_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """將多個事件批量寫入 InterviewSession。

    回傳：{"status": "success", "rows": <int>}（成功筆數）
    """
    if not events:
        return {"status": "success", "rows": 0}

    session = SessionLocal()
    try:
        user_id_int = _user_id_to_int_or_none(user_id)
        rows = [
            InterviewSession(
                user_id=user_id_int,
                session_data=json.dumps(ev, ensure_ascii=False),
            )
            for ev in events
        ]
        session.add_all(rows)
        session.commit()
        return {"status": "success", "rows": len(rows)}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


def clear_user_sessions(user_id: str) -> Dict[str, Any]:
    """刪除該使用者的所有 InterviewSession 記錄。"""
    session = SessionLocal()
    try:
        user_id_int = _user_id_to_int_or_none(user_id)
        if user_id_int is None:
            # 非數字使用者，遵循現有邏輯清除 user_id is NULL
            session.query(InterviewSession).filter(InterviewSession.user_id.is_(None)).delete()
        else:
            session.query(InterviewSession).filter(InterviewSession.user_id == user_id_int).delete()
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


__all__ = [
    "persist_event_to_db",
    "persist_events_to_db",
    "clear_user_sessions",
]


