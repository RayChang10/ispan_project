# 檔案：01_preprocess_embed.py (支援多檔案處理版本)
import pandas as pd
from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
import time
import os
import numpy as np
import pickle
import glob

# ==============================================================================
# 🛠️ 1. 參數設定
# ==============================================================================
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
COLLECTION_NAME = "job_postings_openai"
client = OpenAI(api_key="sk-...") # <--- 請填入您的 OpenAI API Key
JOBS_DIR = "data/raw/jobs"  # 職缺資料夾路徑
MODEL_NAME = "text-embedding-3-small"
EMBEDDING_DIM = 1536
EMBEDDINGS_PATH = "data/processed/embeddings.npy"
CHUNKS_PATH = "data/processed/chunks.pkl"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
TEXT_FIELDS_TO_COMBINE = ["職缺名稱", "公司名稱", "職缺描述", "職務需求", "擅長工具", "工作技能", "其他條件"]
EMBEDDING_BATCH_SIZE = 500
API_RETRY_DELAY = 5
INSERT_BATCH_SIZE = 1000

# ==============================================================================
# 🏢 2. Milvus Collection 結構定義
# ==============================================================================
def create_milvus_collection_if_not_exists():
    if utility.has_collection(COLLECTION_NAME):
        return Collection(COLLECTION_NAME)
    
    print(f"Collection '{COLLECTION_NAME}' 不存在，開始建立...")
    fields = [
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128, is_primary=True),  # 增加長度以支援檔案名
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
        FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=256),  # 新增來源檔案欄位
    ]
    schema = CollectionSchema(fields, description="Job postings collection using OpenAI embeddings")
    collection = Collection(name=COLLECTION_NAME, schema=schema)
    
    print("正在為 embedding 欄位建立索引...")
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
        # 使用 glob 掃描所有 CSV 檔案，排除 Zone.Identifier 檔案
        pattern = os.path.join(directory_path, "*.csv")
        all_files = glob.glob(pattern)
        for file in all_files:
            if not file.endswith(':Zone.Identifier'):
                csv_files.append(file)
    return sorted(csv_files)  # 排序確保處理順序一致

def process_csv_files(csv_files):
    """處理多個 CSV 檔案"""
    all_chunks = []
    total_rows = 0
    
    for csv_file in csv_files:
        print(f"\n--- 正在處理檔案: {os.path.basename(csv_file)} ---")
        try:
            df = pd.read_csv(csv_file)
            print(f"✅ 成功讀取 {len(df)} 筆資料")
            
            # 資料清理
            for col in TEXT_FIELDS_TO_COMBINE + ["上班地點", "工作經歷要求", "職缺連結"]: 
                df[col] = df[col].fillna('')
            for col in ["薪資下限", "薪資上限"]: 
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
            # 文字組合
            df['text_to_embed'] = df[TEXT_FIELDS_TO_COMBINE].apply(
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
                        "location": row['上班地點'],
                        "experience_req": row['工作經歷要求'],
                        "salary_min": row['薪資下限'],
                        "salary_max": row['薪資上限'],
                        "job_url": row['職缺連結'],
                        "source_file": os.path.basename(csv_file)  # 新增來源檔案標記
                    })
                    file_chunks += 1
            
            total_rows += len(df)
            print(f"✅ 檔案處理完成，產生 {file_chunks} 個文字區塊")
            
        except Exception as e:
            print(f"❌ 處理檔案 {csv_file} 時發生錯誤: {e}")
            continue
    
    print(f"\n 所有檔案處理完成！總共處理 {len(csv_files)} 個檔案，{total_rows} 筆資料，產生 {len(all_chunks)} 個文字區塊")
    return all_chunks

# ==============================================================================
# 🚀 4. OpenAI Embedding 函式
# ==============================================================================
def get_openai_embeddings(texts):
    all_embeddings = []
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]
        try:
            print(f"  > 正在向 OpenAI API 請求 {len(batch)} 筆 embedding...")
            response = client.embeddings.create(input=batch, model=MODEL_NAME)
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
            time.sleep(1) 
        except Exception as e:
            print(f"❌ OpenAI API 呼叫失敗: {e}。等待 {API_RETRY_DELAY} 秒後重試...")
            time.sleep(API_RETRY_DELAY)
    return all_embeddings

# ==============================================================================
# 🎯 5. 主程式
# ==============================================================================
def main():
    all_chunks = []
    embeddings = np.array([])

    # 檢查快取檔案
    if os.path.exists(EMBEDDINGS_PATH) and os.path.exists(CHUNKS_PATH):
        print(f"--- 偵測到本地檔案，正在載入... ---")
        with open(CHUNKS_PATH, 'rb') as f: 
            all_chunks = pickle.load(f)
        embeddings = np.load(EMBEDDINGS_PATH)
        print(f"✅ 成功載入 {len(all_chunks)} 個 chunks 和 {len(embeddings)} 個 embeddings。")
    else:
        print(f"--- 未偵測到本地檔案，開始完整處理流程... ---")
        
        # 掃描 CSV 檔案
        csv_files = get_csv_files_from_directory(JOBS_DIR)
        if not csv_files:
            print(f"❌ 錯誤：在 '{JOBS_DIR}' 資料夾中找不到任何 CSV 檔案。")
            return
        
        print(f"📁 找到 {len(csv_files)} 個 CSV 檔案:")
        for file in csv_files:
            print(f"  - {os.path.basename(file)}")
        
        # 處理所有 CSV 檔案
        all_chunks = process_csv_files(csv_files)
        
        if not all_chunks:
            print("❌ 沒有產生任何文字區塊，程式結束。")
            return
        
        # 向量化
        print("\n--- 正在向量化 (使用 OpenAI API)... ---")
        start_time = time.time()
        chunk_texts = [chunk['original_text'] for chunk in all_chunks]
        embeddings_list = get_openai_embeddings(chunk_texts)
        
        if len(embeddings_list) != len(all_chunks):
            print("❌ 向量化失敗，程式終止。")
            return
        
        embeddings = np.array(embeddings_list)
        print(f"✅ 向量化完成！耗時 {time.time() - start_time:.2f} 秒。")
        
        # 儲存結果
        print("\n--- 正在將結果儲存至本地... ---")
        with open(CHUNKS_PATH, 'wb') as f: 
            pickle.dump(all_chunks, f)
        print(f"✅ Chunks 已儲存至 '{CHUNKS_PATH}'")
        np.save(EMBEDDINGS_PATH, embeddings)
        print(f"✅ Embeddings 已儲存至 '{EMBEDDINGS_PATH}'")

    # 上傳到 Milvus
    if not all_chunks or embeddings.size == 0:
        print("沒有資料可上傳，程式結束。")
        return
        
    print("\n--- 步驟 4: 連線 Milvus 並上傳資料 ---")
    try:
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        collection = create_milvus_collection_if_not_exists()
        if collection.num_entities > 0: 
            print(f"⚠️ Collection 中已有 {collection.num_entities} 筆資料。")
        
        for i in range(0, len(all_chunks), INSERT_BATCH_SIZE):
            batch_end = min(i + INSERT_BATCH_SIZE, len(all_chunks))
            print(f"  > 正在上傳批次 {i // INSERT_BATCH_SIZE + 1} (資料 {i+1}-{batch_end})...")
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
                [chunk['source_file'] for chunk in all_chunks[i:batch_end]]  # 新增來源檔案
            ]
            collection.insert(data_to_insert)
        
        collection.flush()
        print(f"\n🎉 所有資料上傳成功！ Collection '{COLLECTION_NAME}' 中目前總共有 {collection.num_entities} 筆資料。")
    except Exception as e:
        print(f"❌ 在與 Milvus 互動時發生錯誤: {e}")
    finally:
        if "default" in connections.list_connections():
            connections.disconnect("default")
            print("✅ Milvus 連線已中斷。")

if __name__ == "__main__":
    main()