#!/usr/bin/env python3
"""
用戶狀態檢查工具
用於檢查特定用戶的實際狀態
"""

import os
import sys
from pathlib import Path

# 添加路徑
sys.path.append(str(Path(__file__).parent))

from virtual_interviewer.app import InterviewAPI, InterviewState


def check_user_state(user_id="default_user"):
    """檢查特定用戶的狀態"""
    print(f"🔍 檢查用戶 {user_id} 的狀態")
    print("=" * 50)

    # 創建 InterviewAPI 實例
    api = InterviewAPI()

    # 檢查初始狀態
    initial_state = api._get_user_state(user_id)
    print(f"🎯 初始狀態: {initial_state.value}")

    # 檢查狀態轉換邏輯
    test_messages = ["你好", "介紹完了", "開始面試", "重新介紹"]

    for message in test_messages:
        print(f"\n📝 測試訊息: '{message}'")
        before_state = api._get_user_state(user_id)
        print(f"🔄 轉換前狀態: {before_state.value}")

        state_changed = api._transition_state(user_id, message)
        after_state = api._get_user_state(user_id)

        if state_changed:
            print(f"✅ 狀態已轉換: {before_state.value} → {after_state.value}")
        else:
            print(f"⏸️ 狀態未轉換: {before_state.value}")

    # 顯示最終狀態
    final_state = api._get_user_state(user_id)
    print(f"\n🎯 最終狀態: {final_state.value}")

    # 顯示所有用戶的狀態
    print(f"\n📊 所有用戶狀態:")
    for uid, state in api.session_states.items():
        print(f"  - 用戶 {uid}: {state.value}")

    return final_state


def reset_user_state(user_id="default_user"):
    """重置用戶狀態"""
    print(f"🔄 重置用戶 {user_id} 的狀態")

    api = InterviewAPI()
    api._set_user_state(user_id, InterviewState.INTRO)

    print(f"✅ 用戶 {user_id} 狀態已重置為: {InterviewState.INTRO.value}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="檢查用戶狀態")
    parser.add_argument("--user-id", default="default_user", help="用戶ID")
    parser.add_argument("--reset", action="store_true", help="重置用戶狀態")

    args = parser.parse_args()

    if args.reset:
        reset_user_state(args.user_id)
    else:
        check_user_state(args.user_id)
