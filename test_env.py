#!/usr/bin/env python3
"""
環境變數測試腳本
用於驗證 .env 檔案設定是否正確
"""

import os

from dotenv import load_dotenv


def test_env_variables():
    """測試環境變數是否正確載入"""
    print("🔍 測試環境變數設定...")

    # 載入環境變數
    load_dotenv()

    # 檢查必要的環境變數
    required_vars = {"OPENAI_API_KEY": "OpenAI API 金鑰"}

    all_good = True

    for var_name, description in required_vars.items():
        value = os.environ.get(var_name)
        if value:
            # 隱藏敏感資訊
            masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            print(f"✅ {description}: {masked_value}")
        else:
            print(f"❌ {description}: 未設定")
            all_good = False

    # 檢查可選的環境變數
    optional_vars = {"PYTHONPATH": "Python 路徑", "PYTHONUNBUFFERED": "Python 輸出緩衝"}

    for var_name, description in optional_vars.items():
        value = os.environ.get(var_name)
        if value:
            print(f"ℹ️  {description}: {value}")
        else:
            print(f"ℹ️  {description}: 未設定（可選）")

    if all_good:
        print("\n🎉 所有必要的環境變數都已正確設定！")
        return True
    else:
        print("\n⚠️  請檢查 .env 檔案設定")
        return False


if __name__ == "__main__":
    test_env_variables()
