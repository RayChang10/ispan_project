#!/usr/bin/env python3
"""
虛擬面試顧問 - 啟動腳本
Virtual Interview Consultant - Startup Script
"""

import os
import sys

from app import app, db


def create_database():
    """建立資料庫表格"""
    try:
        with app.app_context():
            db.create_all()
            print("✅ 資料庫初始化成功")
    except Exception as e:
        print(f"❌ 資料庫初始化失敗: {e}")
        return False
    return True

def check_requirements():
    """檢查環境需求"""
    try:
        import flask
        import flask_cors
        import flask_restful
        import flask_sqlalchemy
        print("✅ 所有必要套件已安裝")
        return True
    except ImportError as e:
        print(f"❌ 缺少必要套件: {e}")
        print("請執行: pip install -r requirements.txt")
        return False

def main():
    """主啟動函數"""
    print("🚀 虛擬面試顧問啟動中...")
    print("=" * 50)
    
    # 檢查套件
    if not check_requirements():
        sys.exit(1)
    
    # 初始化資料庫
    if not create_database():
        sys.exit(1)
    
    # 啟動應用
    print(f"🌐 應用程式將在 http://localhost:5000 啟動")
    print("📝 主頁面: http://localhost:5000")
    print("📋 履歷建立: http://localhost:5000/resume")
    print("=" * 50)
    print("按 Ctrl+C 停止應用程式")
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True
        )
    except KeyboardInterrupt:
        print("\n👋 應用程式已停止")
    except Exception as e:
        print(f"❌ 應用程式啟動失敗: {e}")

if __name__ == '__main__':
    main() 