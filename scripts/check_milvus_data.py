#!/usr/bin/env python3
"""
Milvus 資料寫入狀態檢查腳本
檢查 Milvus 向量資料庫的連接狀態、集合存在性、資料數量等
"""

import os
import sys
from pathlib import Path
import time

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 載入環境變數
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv 未安裝，直接讀取環境變數")

def check_milvus_connection():
    """檢查 Milvus 連接狀態"""
    print("🔍 檢查 Milvus 連接狀態...")
    
    try:
        from pymilvus import connections, utility
        
        # 連接參數
        host = os.getenv("MILVUS_HOST", "localhost")
        port = os.getenv("MILVUS_PORT", "19530")
        
        # 如果在本地環境運行，但 Milvus 在 Docker 中，使用 localhost
        if host == "milvus" and not os.path.exists("/.dockerenv"):
            host = "localhost"
            print(f"  - 檢測到本地環境，調整連接目標為: {host}:{port}")
        
        print(f"  - 連接目標: {host}:{port}")
        
        # 嘗試連接
        connections.connect("default", host=host, port=port)
        
        # 檢查連接狀態
        if connections.has_connection("default"):
            print("✅ Milvus 連接成功！")
            return True
        else:
            print("❌ Milvus 連接失敗")
            return False
            
    except Exception as e:
        print(f"❌ Milvus 連接錯誤: {e}")
        return False

def check_collections():
    """檢查所有集合"""
    print("\n📊 檢查 Milvus 集合...")
    
    try:
        from pymilvus import utility, Collection
        
        # 獲取所有集合
        collections = utility.list_collections()
        
        if not collections:
            print("⚠️ 沒有找到任何集合")
            return []
        
        print(f"✅ 找到 {len(collections)} 個集合:")
        
        collection_info = []
        for collection_name in collections:
            try:
                collection = Collection(collection_name)
                collection.load()
                
                # 獲取集合資訊
                num_entities = collection.num_entities
                schema = collection.schema
                
                print(f"  📁 {collection_name}:")
                print(f"    - 實體數量: {num_entities:,}")
                print(f"    - 欄位數量: {len(schema.fields)}")
                
                # 顯示欄位資訊
                for field in schema.fields:
                    print(f"    - {field.name}: {field.dtype}")
                
                collection_info.append({
                    "name": collection_name,
                    "entities": num_entities,
                    "fields": len(schema.fields)
                })
                
            except Exception as e:
                print(f"  ❌ 無法讀取集合 {collection_name}: {e}")
        
        return collection_info
        
    except Exception as e:
        print(f"❌ 檢查集合時發生錯誤: {e}")
        return []

def check_job_collection():
    """檢查職缺集合的詳細資訊"""
    print("\n💼 檢查職缺集合詳細資訊...")
    
    try:
        from pymilvus import Collection, utility
        
        collection_name = "job_postings_openai"
        
        if not utility.has_collection(collection_name):
            print(f"❌ 集合 '{collection_name}' 不存在")
            return None
        
        collection = Collection(collection_name)
        collection.load()
        
        print(f"✅ 集合 '{collection_name}' 資訊:")
        print(f"  - 總實體數量: {collection.num_entities:,}")
        
        # 檢查索引
        index_info = collection.index()
        if index_info:
            print(f"  - 索引狀態: 已建立")
            print(f"  - 索引類型: {index_info.params}")
        else:
            print(f"  - 索引狀態: 未建立")
        
        # 檢查欄位
        schema = collection.schema
        print(f"  - 欄位資訊:")
        for field in schema.fields:
            print(f"    * {field.name}: {field.dtype}")
        
        return collection
        
    except Exception as e:
        print(f"❌ 檢查職缺集合時發生錯誤: {e}")
        return None

def test_vector_search():
    """測試向量搜尋功能"""
    print("\n🔍 測試向量搜尋功能...")
    
    try:
        from pymilvus import Collection, utility
        import numpy as np
        
        collection_name = "job_postings_openai"
        
        if not utility.has_collection(collection_name):
            print(f"❌ 集合 '{collection_name}' 不存在，無法測試搜尋")
            return False
        
        collection = Collection(collection_name)
        collection.load()
        
        if collection.num_entities == 0:
            print("⚠️ 集合中沒有資料，無法測試搜尋")
            return False
        
        # 創建測試向量
        test_vector = np.random.rand(1536).tolist()
        
        # 執行搜尋
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10},
        }
        
        print("  - 執行向量搜尋測試...")
        results = collection.search(
            data=[test_vector],
            anns_field="embedding",
            param=search_params,
            limit=3,
            output_fields=["job_title", "company_name", "location"]
        )
        
        if results and len(results[0]) > 0:
            print(f"✅ 向量搜尋測試成功！找到 {len(results[0])} 個結果")
            
            # 顯示前幾個結果
            for i, hit in enumerate(results[0][:2]):
                print(f"    {i+1}. {hit.entity.get('job_title', '未知')} - {hit.entity.get('company_name', '未知')}")
                print(f"       相似度: {hit.score:.4f}")
            
            return True
        else:
            print("⚠️ 向量搜尋無結果")
            return False
            
    except Exception as e:
        print(f"❌ 向量搜尋測試失敗: {e}")
        return False

def check_data_quality():
    """檢查資料品質"""
    print("\n📈 檢查資料品質...")
    
    try:
        from pymilvus import Collection, utility
        
        collection_name = "job_postings_openai"
        
        if not utility.has_collection(collection_name):
            print(f"❌ 集合 '{collection_name}' 不存在")
            return
        
        collection = Collection(collection_name)
        collection.load()
        
        # 檢查是否有資料
        if collection.num_entities == 0:
            print("⚠️ 集合中沒有資料")
            return
        
        # 檢查欄位資料完整性
        print("  - 檢查欄位資料完整性...")
        
        # 執行查詢檢查各欄位
        results = collection.query(
            expr="",
            output_fields=["job_title", "company_name", "location", "job_url"],
            limit=10
        )
        
        if results:
            print(f"✅ 成功查詢到 {len(results)} 筆資料")
            
            # 檢查資料完整性
            complete_records = 0
            for record in results:
                if (record.get('job_title') and 
                    record.get('company_name') and 
                    record.get('location')):
                    complete_records += 1
            
            completeness_rate = (complete_records / len(results)) * 100
            print(f"  - 資料完整性: {completeness_rate:.1f}% ({complete_records}/{len(results)})")
            
            # 顯示範例資料
            print("  - 範例資料:")
            for i, record in enumerate(results[:3]):
                print(f"    {i+1}. {record.get('job_title', 'N/A')} - {record.get('company_name', 'N/A')}")
        else:
            print("⚠️ 無法查詢到資料")
            
    except Exception as e:
        print(f"❌ 檢查資料品質時發生錯誤: {e}")

def main():
    """主函數"""
    print("🚀 Milvus 資料寫入狀態檢查")
    print("=" * 50)
    
    # 1. 檢查連接
    if not check_milvus_connection():
        print("\n❌ Milvus 連接失敗，請檢查:")
        print("  - Milvus 服務是否正在運行")
        print("  - 連接參數是否正確 (MILVUS_HOST, MILVUS_PORT)")
        print("  - 網路連接是否正常")
        return
    
    # 2. 檢查集合
    collections = check_collections()
    
    # 3. 檢查職缺集合
    job_collection = check_job_collection()
    
    # 4. 測試向量搜尋
    if job_collection and job_collection.num_entities > 0:
        test_vector_search()
    
    # 5. 檢查資料品質
    check_data_quality()
    
    print("\n" + "=" * 50)
    print("✅ 檢查完成！")
    
    # 總結
    if collections:
        total_entities = sum(c['entities'] for c in collections)
        print(f"📊 總計: {len(collections)} 個集合，{total_entities:,} 筆資料")
    else:
        print("⚠️ 沒有找到任何資料")

if __name__ == "__main__":
    main()
