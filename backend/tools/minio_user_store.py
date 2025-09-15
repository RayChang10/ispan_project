#!/usr/bin/env python3
"""
MinIO 使用者註冊儲存工具

將使用者的 email/name/password 以安全格式寫入 MinIO：
- 密碼以 bcrypt 雜湊後存放
- 物件存放於 users/<email_sanitized>.json（若已存在則報錯）

環境變數（皆具預設值，建議於 .env 設定）：
- MINIO_ENDPOINT (default: localhost:9000)
- MINIO_ACCESS_KEY (default: minioadmin)
- MINIO_SECRET_KEY (default: minioadmin)
- MINIO_SECURE     (default: false)
- MINIO_BUCKET     (default: fastagent-users)
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Tuple

import bcrypt

# 可選導入 dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    # 如果沒有 dotenv，直接從環境變數讀取
    pass


def _get_minio_client_and_bucket():
    """根據環境變數初始化 MinIO client 與 bucket 名稱。"""
    try:
        import importlib

        minio_module = importlib.import_module("minio")
        Minio = getattr(minio_module, "Minio")

        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        bucket = os.getenv("MINIO_BUCKET", "fastagent-users")

        client = Minio(
            endpoint, access_key=access_key, secret_key=secret_key, secure=secure
        )

        # 確保 bucket 存在
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        return client, bucket
    except Exception as e:
        raise RuntimeError(f"MinIO 初始化失敗：{e}")


def _sanitize_email_for_object(email: str) -> str:
    return (
        email.lower()
        .replace("@", "_at_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("..", ".")
    )


def register_user_to_minio(email: str, password: str, name: str) -> Dict[str, Any]:
    """將註冊資料存入 MinIO（作為 JSON 檔）。

    回傳：{"status": "success"|"error", ...}
    """
    # 基本驗證（與前端規則對齊）
    if not email or len(email) < 8 or len(email) > 64:
        return {"status": "error", "message": "帳號長度需 8–64 字"}
    if not password or len(password) < 8 or len(password) > 64:
        return {"status": "error", "message": "密碼需 8–64 字"}
    if not name or len(name) > 50:
        return {"status": "error", "message": "姓名必填且不超過 50 字"}

    try:
        client, bucket = _get_minio_client_and_bucket()

        safe_email = _sanitize_email_for_object(email)
        object_name = f"users/{safe_email}.json"

        # 檢查是否已存在
        try:
            client.stat_object(bucket, object_name)
            return {"status": "error", "message": "此 Email 已註冊"}
        except Exception:
            pass

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        payload = {
            "email": email,
            "name": name,
            "password_hash": password_hash.decode("utf-8", errors="ignore"),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "version": 1,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=BytesIO(body),
            length=len(body),
            content_type="application/json",
        )

        return {
            "status": "success",
            "message": "註冊資料已寫入 MinIO",
            "object_name": object_name,
            "bucket": bucket,
        }
    except Exception as e:
        return {"status": "error", "message": f"寫入 MinIO 失敗: {str(e)}"}


# 供外部 import
def verify_user_from_minio(email: str, password: str) -> Dict[str, Any]:
    """從 MinIO 讀取使用者檔案並驗證密碼。"""
    if not email or not password:
        return {"status": "error", "message": "帳號與密碼必填"}

    try:
        client, bucket = _get_minio_client_and_bucket()
        safe_email = _sanitize_email_for_object(email)
        object_name = f"users/{safe_email}.json"

        # 嘗試讀取
        data = client.get_object(bucket, object_name)
        try:
            content = data.read()
        finally:
            data.close()
            data.release_conn()

        payload = json.loads(content.decode("utf-8"))
        stored_hash = payload.get("password_hash", "").encode("utf-8")
        if not stored_hash:
            return {"status": "error", "message": "帳號資料不完整"}

        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return {
                "status": "success",
                "user": {
                    "email": payload.get("email", email),
                    "name": payload.get("name", "會員"),
                },
            }
        return {"status": "error", "message": "帳號或密碼不正確"}
    except Exception as e:
        return {"status": "error", "message": f"登入驗證失敗: {str(e)}"}


__all__ = ["register_user_to_minio", "verify_user_from_minio"]
