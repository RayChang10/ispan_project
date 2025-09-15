#!/usr/bin/env python3
"""
資料庫初始化腳本
用於建立 PostgreSQL 表格
"""

import os
import sys

# 添加 backend 目錄到 Python 路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))


def main():
    """主函數"""
    print("🚀 開始初始化資料庫...")
    
    try:
        # 測試資料庫連接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ 資料庫連接成功: {version}")
        
        # 建立表格
        print("📋 建立資料表...")
        create_tables_safely()
        print("✅ 資料表建立完成")
        
        # 驗證表格是否建立
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"📊 已建立的表格: {', '.join(tables)}")
            else:
                print("⚠️ 沒有找到任何表格")
                
    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("🎉 資料庫初始化完成！")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
