#!/usr/bin/env python3
"""
設定職缺搜尋資料庫腳本
將 commitLLM 的職缺資料匯入到 Milvus 向量資料庫中
"""

import os
import sys
import pandas as pd
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
import time
import numpy as np
import pickle
import glob

# 載入環境變數
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv 未安裝，直接讀取環境變數")

# ==============================================================================
# 🛠️ 1. 參數設定
# ==============================================================================
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
COLLECTION_NAME = "job_postings_openai"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("❌ 錯誤：請設定 OPENAI_API_KEY 環境變數")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)
JOBS_DIR = str(project_root / "commitLLM" / "data" / "raw" / "jobs")
MODEL_NAME = "text-embedding-3-small"
EMBEDDING_DIM = 1536
EMBEDDINGS_PATH = str(project_root / "commitLLM" / "data" / "processed" / "embeddings.npy")
CHUNKS_PATH = str(project_root / "commitLLM" / "data" / "processed" / "chunks.pkl")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
TEXT_FIELDS_TO_COMBINE = ["職缺名稱", "公司名稱", "職缺描述", "職務需求", "擅長工具", "工作技能", "其他條件"]
EMBEDDING_BATCH_SIZE = 500
API_RETRY_DELAY = 5
INSERT_BATCH_SIZE = 1000

print(f"🔧 配置資訊:")
print(f"  - Milvus: {MILVUS_HOST}:{MILVUS_PORT}")
print(f"  - Collection: {COLLECTION_NAME}")
print(f"  - 職缺資料目錄: {JOBS_DIR}")
print(f"  - OpenAI Model: {MODEL_NAME}")

# ==============================================================================
# 🏢 2. Milvus Collection 結構定義
# ==============================================================================
def create_milvus_collection_if_not_exists():
    """建立 Milvus Collection（如果不存在）"""
    if utility.has_collection(COLLECTION_NAME):
        print(f"✅ Collection '{COLLECTION_NAME}' 已存在")
        return Collection(COLLECTION_NAME)
    
    print(f"🏗️ Collection '{COLLECTION_NAME}' 不存在，開始建立...")
    fields = [
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128, is_primary=True),
        FieldSchema(name="original_text", dtype=DataType.VARCHAR, max_length=8192), 
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        FieldSchema(name="job_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="job_title", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="company_name", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="location", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="experience_req", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="salary_min", dtype=DataType.INT64),
        FieldSchema(name="salary_max", dtype=DataType.INT64),
        FieldSchema(name="job_url", dtype=DataType.VARCHAR, max_length=2048),
        FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=256),
    ]
    schema = CollectionSchema(fields, description="Job postings collection using OpenAI embeddings")
    collection = Collection(name=COLLECTION_NAME, schema=schema)
    
    print("🔍 正在為 embedding 欄位建立索引...")
    index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
    collection.create_index(field_name="embedding", index_params=index_params)
    print(f"✅ Collection '{COLLECTION_NAME}' 與索引建立完成！")
    return collection

# ==============================================================================
# 📁 3. 檔案掃描與處理函式
# ==============================================================================
def get_csv_files_from_directory(directory_path):
    """掃描指定資料夾中的所有 CSV 檔案"""
    csv_files = []
    if os.path.exists(directory_path):
        pattern = os.path.join(directory_path, "*.csv")
        all_files = glob.glob(pattern)
        for file in all_files:
            if not file.endswith(':Zone.Identifier'):
                csv_files.append(file)
    return sorted(csv_files)

def process_csv_files(csv_files):
    """處理多個 CSV 檔案"""
    all_chunks = []
    total_rows = 0
    
    for csv_file in csv_files:
        print(f"\n📄 正在處理檔案: {os.path.basename(csv_file)}")
        try:
            df = pd.read_csv(csv_file)
            print(f"✅ 成功讀取 {len(df)} 筆資料")
            
            # 檢查必要欄位
            required_fields = ["job_id", "職缺名稱", "公司名稱"]
            missing_fields = [field for field in required_fields if field not in df.columns]
            if missing_fields:
                print(f"❌ 缺少必要欄位: {missing_fields}")
                continue
            
            # 資料清理
            for col in TEXT_FIELDS_TO_COMBINE + ["上班地點", "工作經歷要求", "職缺連結"]: 
                if col in df.columns:
                    df[col] = df[col].fillna('')
            
            for col in ["薪資下限", "薪資上限"]: 
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
            # 文字組合
            text_fields = [col for col in TEXT_FIELDS_TO_COMBINE if col in df.columns]
            df['text_to_embed'] = df[text_fields].apply(
                lambda x: "\n".join(f"{col}: {val}" for col, val in x.items() if val), axis=1
            )
            
            # 文字切割
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
            file_chunks = 0
            
            for index, row in df.iterrows():
                chunks = text_splitter.split_text(row['text_to_embed'])
                for i, chunk_text in enumerate(chunks):
                    all_chunks.append({
                        "chunk_id": f"{os.path.basename(csv_file)}_{row['job_id']}_{i}",
                        "original_text": chunk_text,
                        "job_id": str(row['job_id']),
                        "job_title": row['職缺名稱'],
                        "company_name": row['公司名稱'],
                        "location": row.get('上班地點', ''),
                        "experience_req": row.get('工作經歷要求', ''),
                        "salary_min": row.get('薪資下限', 0),
                        "salary_max": row.get('薪資上限', 0),
                        "job_url": row.get('職缺連結', ''),
                        "source_file": os.path.basename(csv_file)
                    })
                    file_chunks += 1
            
            total_rows += len(df)
            print(f"✅ 檔案處理完成，產生 {file_chunks} 個文字區塊")
            
        except Exception as e:
            print(f"❌ 處理檔案 {csv_file} 時發生錯誤: {e}")
            continue
    
    print(f"\n🎯 所有檔案處理完成！")
    print(f"  - 處理檔案數: {len(csv_files)}")
    print(f"  - 總職缺數: {total_rows}")
    print(f"  - 文字區塊數: {len(all_chunks)}")
    return all_chunks

# ==============================================================================
# 🚀 4. OpenAI Embedding 函式
# ==============================================================================
def get_openai_embeddings(texts):
    """使用 OpenAI API 生成 embeddings"""
    all_embeddings = []
    total_batches = (len(texts) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch_num = i // EMBEDDING_BATCH_SIZE + 1
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]
        
        try:
            print(f"🤖 正在處理批次 {batch_num}/{total_batches} ({len(batch)} 個文字區塊)...")
            response = client.embeddings.create(input=batch, model=MODEL_NAME)
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
            time.sleep(1)  # 避免 API 限制
        except Exception as e:
            print(f"❌ OpenAI API 呼叫失敗: {e}。等待 {API_RETRY_DELAY} 秒後重試...")
            time.sleep(API_RETRY_DELAY)
            # 重試一次
            try:
                response = client.embeddings.create(input=batch, model=MODEL_NAME)
                embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(embeddings)
            except Exception as retry_e:
                print(f"❌ 重試失敗: {retry_e}")
                return None
    
    return all_embeddings

# ==============================================================================
# 🎯 5. 主程式
# ==============================================================================
def main():
    """主要執行流程"""
    print("🚀 開始設定職缺搜尋資料庫...")
    
    all_chunks = []
    embeddings = np.array([])

    # 檢查快取檔案
    if os.path.exists(EMBEDDINGS_PATH) and os.path.exists(CHUNKS_PATH):
        print(f"📂 偵測到快取檔案，正在載入...")
        try:
            with open(CHUNKS_PATH, 'rb') as f: 
                all_chunks = pickle.load(f)
            embeddings = np.load(EMBEDDINGS_PATH)
            print(f"✅ 成功載入 {len(all_chunks)} 個 chunks 和 {len(embeddings)} 個 embeddings")
        except Exception as e:
            print(f"❌ 載入快取檔案失敗: {e}")
            print("🔄 將重新處理資料...")
            all_chunks = []
            embeddings = np.array([])
    
    # 如果沒有快取或載入失敗，重新處理
    if not all_chunks or embeddings.size == 0:
        print(f"🔍 掃描職缺資料目錄: {JOBS_DIR}")
        
        # 掃描 CSV 檔案
        csv_files = get_csv_files_from_directory(JOBS_DIR)
        if not csv_files:
            print(f"❌ 錯誤：在 '{JOBS_DIR}' 資料夾中找不到任何 CSV 檔案")
            return False
        
        print(f"📁 找到 {len(csv_files)} 個 CSV 檔案:")
        for file in csv_files:
            print(f"  - {os.path.basename(file)}")
        
        # 處理所有 CSV 檔案
        all_chunks = process_csv_files(csv_files)
        
        if not all_chunks:
            print("❌ 沒有產生任何文字區塊，程式結束")
            return False
        
        # 向量化
        print("\n🤖 正在使用 OpenAI API 進行向量化...")
        start_time = time.time()
        chunk_texts = [chunk['original_text'] for chunk in all_chunks]
        embeddings_list = get_openai_embeddings(chunk_texts)
        
        if not embeddings_list or len(embeddings_list) != len(all_chunks):
            print("❌ 向量化失敗，程式終止")
            return False
        
        embeddings = np.array(embeddings_list)
        print(f"✅ 向量化完成！耗時 {time.time() - start_time:.2f} 秒")
        
        # 儲存結果
        print("\n💾 正在儲存快取檔案...")
        os.makedirs(os.path.dirname(CHUNKS_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(EMBEDDINGS_PATH), exist_ok=True)
        
        with open(CHUNKS_PATH, 'wb') as f: 
            pickle.dump(all_chunks, f)
        print(f"✅ Chunks 已儲存至 '{CHUNKS_PATH}'")
        
        np.save(EMBEDDINGS_PATH, embeddings)
        print(f"✅ Embeddings 已儲存至 '{EMBEDDINGS_PATH}'")

    # 上傳到 Milvus
    print(f"\n🗄️ 正在連線到 Milvus ({MILVUS_HOST}:{MILVUS_PORT})...")
    try:
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        print("✅ Milvus 連線成功")
        
        collection = create_milvus_collection_if_not_exists()
        existing_count = collection.num_entities
        
        if existing_count > 0: 
            print(f"⚠️ Collection 中已有 {existing_count} 筆資料")
            user_input = input("是否要清空現有資料並重新匯入？(y/N): ")
            if user_input.lower() == 'y':
                collection.drop()
                print("🗑️ 已清空現有資料")
                collection = create_milvus_collection_if_not_exists()
            else:
                print("ℹ️ 跳過資料匯入")
                return True
        
        # 分批上傳資料
        total_batches = (len(all_chunks) + INSERT_BATCH_SIZE - 1) // INSERT_BATCH_SIZE
        print(f"📤 開始上傳資料 ({total_batches} 個批次)...")
        
        for i in range(0, len(all_chunks), INSERT_BATCH_SIZE):
            batch_num = i // INSERT_BATCH_SIZE + 1
            batch_end = min(i + INSERT_BATCH_SIZE, len(all_chunks))
            
            print(f"  📦 上傳批次 {batch_num}/{total_batches} (第 {i+1}-{batch_end} 筆資料)...")
            
            data_to_insert = [
                [chunk['chunk_id'] for chunk in all_chunks[i:batch_end]],
                [chunk['original_text'] for chunk in all_chunks[i:batch_end]],
                embeddings[i:batch_end].tolist(),
                [chunk['job_id'] for chunk in all_chunks[i:batch_end]],
                [chunk['job_title'] for chunk in all_chunks[i:batch_end]],
                [chunk['company_name'] for chunk in all_chunks[i:batch_end]],
                [chunk['location'] for chunk in all_chunks[i:batch_end]],
                [chunk['experience_req'] for chunk in all_chunks[i:batch_end]],
                [chunk['salary_min'] for chunk in all_chunks[i:batch_end]],
                [chunk['salary_max'] for chunk in all_chunks[i:batch_end]],
                [chunk['job_url'] for chunk in all_chunks[i:batch_end]],
                [chunk['source_file'] for chunk in all_chunks[i:batch_end]]
            ]
            collection.insert(data_to_insert)
        
        collection.flush()
        final_count = collection.num_entities
        print(f"\n🎉 資料上傳完成！")
        print(f"  - Collection: {COLLECTION_NAME}")
        print(f"  - 總筆數: {final_count}")
        print(f"  - 新增筆數: {final_count - existing_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Milvus 操作失敗: {e}")
        return False
    finally:
        if "default" in connections.list_connections():
            connections.disconnect("default")
            print("✅ Milvus 連線已中斷")

def test_search():
    """測試搜尋功能"""
    print("\n🔍 測試職缺搜尋功能...")
    try:
        from backend.tools.job_search_tool import job_search_tool
        
        # 測試連線
        if not job_search_tool.connect_milvus():
            print("❌ 無法連線到 Milvus")
            return False
        
        # 測試搜尋
        test_query = "Python 開發工程師"
        results = job_search_tool.search_jobs(test_query, top_k=3)
        
        if results:
            print(f"✅ 搜尋測試成功！找到 {len(results)} 個相關職缺:")
            for i, job in enumerate(results, 1):
                print(f"  {i}. {job['job_title']} - {job['company_name']} (相似度: {job['similarity_score']:.3f})")
            return True
        else:
            print("❌ 搜尋測試失敗：沒有找到任何結果")
            return False
            
    except Exception as e:
        print(f"❌ 搜尋測試失敗: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 FastMCP-FastAgent 職缺搜尋資料庫設定")
    print("=" * 60)
    
    # 執行主要設定流程
    if main():
        print("\n" + "=" * 60)
        print("✅ 資料庫設定完成！")
        
        # 測試搜尋功能
        if test_search():
            print("🎯 系統已準備就緒，可以開始使用職缺搜尋功能！")
        else:
            print("⚠️ 搜尋功能測試失敗，請檢查配置")
    else:
        print("\n" + "=" * 60)
        print("❌ 資料庫設定失敗！")
        sys.exit(1)
    
    print("=" * 60)

