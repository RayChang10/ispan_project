#!/usr/bin/env python3
"""
優化版職缺搜尋資料庫設定腳本
解決資料一致性、路徑硬編碼、資料驗證和連接檢查等問題
"""

import os
import sys
import pandas as pd
from pathlib import Path
import hashlib
import json
from datetime import datetime

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
# 🛠️ 1. 優化參數設定
# ==============================================================================
class Config:
    """配置管理類別"""
    
    def __init__(self):
        # Milvus 設定
        self.MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
        self.MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
        self.COLLECTION_NAME = "job_postings_openai"
        
        # OpenAI 設定
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not self.OPENAI_API_KEY:
            raise ValueError("❌ 錯誤：請設定 OPENAI_API_KEY 環境變數")
        
        # 動態路徑設定 - 支援多種專案結構
        self.project_root = Path(__file__).parent.parent
        self.data_root = self._find_data_directory()
        
        # 資料路徑
        self.JOBS_DIR = str(self.data_root / "raw" / "jobs")
        self.EMBEDDINGS_PATH = str(self.data_root / "processed" / "embeddings.npy")
        self.CHUNKS_PATH = str(self.data_root / "processed" / "chunks.pkl")
        self.CACHE_METADATA_PATH = str(self.data_root / "processed" / "cache_metadata.json")
        
        # 模型設定
        self.MODEL_NAME = "text-embedding-3-small"
        self.EMBEDDING_DIM = 1536
        self.CHUNK_SIZE = 1000
        self.CHUNK_OVERLAP = 150
        self.TEXT_FIELDS_TO_COMBINE = [
            "職缺名稱", "公司名稱", "職缺描述", "職務需求", 
            "擅長工具", "工作技能", "其他條件"
        ]
        self.EMBEDDING_BATCH_SIZE = 500
        self.API_RETRY_DELAY = 5
        self.INSERT_BATCH_SIZE = 1000
        
        # 驗證設定
        self.REQUIRED_FIELDS = ["job_id", "職缺名稱", "公司名稱"]
        
    def _find_data_directory(self):
        """尋找資料目錄"""
        data_path = self.project_root / "data"
        
        if data_path.exists():
            print(f"✅ 找到資料目錄: {data_path}")
            return data_path
        else:
            print(f"⚠️ 資料目錄不存在: {data_path}")
            print("請確保專案根目錄下有 data/ 資料夾")
            raise FileNotFoundError(f"資料目錄不存在: {data_path}")
    
    def print_config(self):
        """印出配置資訊"""
        print(f"🔧 優化配置資訊:")
        print(f"  - Milvus: {self.MILVUS_HOST}:{self.MILVUS_PORT}")
        print(f"  - Collection: {self.COLLECTION_NAME}")
        print(f"  - 資料根目錄: {self.data_root}")
        print(f"  - 職缺資料目錄: {self.JOBS_DIR}")
        print(f"  - OpenAI Model: {self.MODEL_NAME}")

# ==============================================================================
# 🔍 2. 資料一致性檢查
# ==============================================================================
class DataConsistencyChecker:
    """資料一致性檢查器"""
    
    def __init__(self, config):
        self.config = config
    
    def calculate_file_hash(self, file_path):
        """計算檔案雜湊值"""
        if not os.path.exists(file_path):
            return None
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_csv_files_info(self):
        """獲取 CSV 檔案資訊"""
        csv_files = self._get_csv_files_from_directory(self.config.JOBS_DIR)
        files_info = {}
        
        for file_path in csv_files:
            files_info[file_path] = {
                'hash': self.calculate_file_hash(file_path),
                'mtime': os.path.getmtime(file_path),
                'size': os.path.getsize(file_path)
            }
        
        return files_info
    
    def _get_csv_files_from_directory(self, directory_path):
        """掃描指定資料夾中的所有 CSV 檔案"""
        csv_files = []
        if os.path.exists(directory_path):
            pattern = os.path.join(directory_path, "*.csv")
            all_files = glob.glob(pattern)
            for file in all_files:
                if not file.endswith(':Zone.Identifier'):
                    csv_files.append(file)
        return sorted(csv_files)
    
    def load_cache_metadata(self):
        """載入快取元資料"""
        if os.path.exists(self.config.CACHE_METADATA_PATH):
            try:
                with open(self.config.CACHE_METADATA_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 載入快取元資料失敗: {e}")
        return None
    
    def save_cache_metadata(self, csv_files_info, chunks_count, embeddings_count):
        """儲存快取元資料"""
        metadata = {
            'created_at': datetime.now().isoformat(),
            'csv_files_info': csv_files_info,
            'chunks_count': chunks_count,
            'embeddings_count': embeddings_count,
            'model_name': self.config.MODEL_NAME,
            'chunk_size': self.config.CHUNK_SIZE,
            'chunk_overlap': self.config.CHUNK_OVERLAP
        }
        
        os.makedirs(os.path.dirname(self.config.CACHE_METADATA_PATH), exist_ok=True)
        with open(self.config.CACHE_METADATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def is_cache_valid(self):
        """檢查快取是否有效"""
        # 檢查快取檔案是否存在
        if not (os.path.exists(self.config.EMBEDDINGS_PATH) and 
                os.path.exists(self.config.CHUNKS_PATH) and
                os.path.exists(self.config.CACHE_METADATA_PATH)):
            print("📂 快取檔案不完整")
            return False
        
        # 載入快取元資料
        metadata = self.load_cache_metadata()
        if not metadata:
            print("📂 快取元資料載入失敗")
            return False
        
        # 檢查 CSV 檔案是否有變更
        current_csv_info = self.get_csv_files_info()
        cached_csv_info = metadata.get('csv_files_info', {})
        
        if current_csv_info != cached_csv_info:
            print("📂 CSV 檔案已變更，快取無效")
            return False
        
        # 檢查模型設定是否一致
        if (metadata.get('model_name') != self.config.MODEL_NAME or
            metadata.get('chunk_size') != self.config.CHUNK_SIZE or
            metadata.get('chunk_overlap') != self.config.CHUNK_OVERLAP):
            print("📂 模型設定已變更，快取無效")
            return False
        
        print("✅ 快取有效")
        return True

# ==============================================================================
# 🔌 3. 連接檢查器
# ==============================================================================
class ConnectionChecker:
    """連接檢查器"""
    
    def __init__(self, config):
        self.config = config
    
    def check_milvus_connection(self):
        """提前檢查 Milvus 連接狀態"""
        print("🔍 檢查 Milvus 連接狀態...")
        try:
            connections.connect("default", host=self.config.MILVUS_HOST, port=self.config.MILVUS_PORT)
            connections.disconnect("default")
            print("✅ Milvus 連接正常")
            return True
        except Exception as e:
            print(f"❌ Milvus 連接失敗: {e}")
            return False
    
    def check_openai_connection(self):
        """檢查 OpenAI API 連接"""
        print("🔍 檢查 OpenAI API 連接...")
        try:
            client = OpenAI(api_key=self.config.OPENAI_API_KEY)
            # 簡單的 API 測試
            response = client.embeddings.create(
                input=["test"], 
                model=self.config.MODEL_NAME
            )
            print("✅ OpenAI API 連接正常")
            return True
        except Exception as e:
            print(f"❌ OpenAI API 連接失敗: {e}")
            return False

# ==============================================================================
# ✅ 4. 資料驗證器
# ==============================================================================
class DataValidator:
    """資料驗證器"""
    
    def __init__(self, config):
        self.config = config
    
    def validate_cache_data(self, chunks, embeddings):
        """驗證快取資料的完整性"""
        print("🔍 驗證快取資料完整性...")
        
        # 檢查基本結構
        if not chunks or not isinstance(chunks, list):
            print("❌ Chunks 資料結構無效")
            return False
        
        if not isinstance(embeddings, np.ndarray) or (embeddings.size == 0):
            print("❌ Embeddings 資料結構無效")
            return False
        
        # 檢查數量一致性
        if len(chunks) != len(embeddings):
            print(f"❌ 資料數量不一致: chunks={len(chunks)}, embeddings={len(embeddings)}")
            return False
        
        # 檢查必要欄位
        required_fields = ['chunk_id', 'original_text', 'job_id', 'job_title', 'company_name']
        for i, chunk in enumerate(chunks[:10]):  # 抽樣檢查前10個
            if not isinstance(chunk, dict):
                print(f"❌ Chunk {i} 不是字典格式")
                return False
            
            missing_fields = [field for field in required_fields if field not in chunk]
            if missing_fields:
                print(f"❌ Chunk {i} 缺少必要欄位: {missing_fields}")
                return False
        
        # 檢查 embedding 維度
        if embeddings.shape[1] != self.config.EMBEDDING_DIM:
            print(f"❌ Embedding 維度不正確: {embeddings.shape[1]} != {self.config.EMBEDDING_DIM}")
            return False
        
        print("✅ 快取資料驗證通過")
        return True
    
    def validate_csv_data(self, csv_files):
        """驗證 CSV 檔案資料"""
        print("🔍 驗證 CSV 檔案資料...")
        
        if not csv_files:
            print("❌ 沒有找到 CSV 檔案")
            return False
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                
                # 檢查必要欄位
                missing_fields = [field for field in self.config.REQUIRED_FIELDS if field not in df.columns]
                if missing_fields:
                    print(f"❌ {os.path.basename(csv_file)} 缺少必要欄位: {missing_fields}")
                    return False
                
                # 檢查資料是否為空
                if len(df) == 0:
                    print(f"❌ {os.path.basename(csv_file)} 沒有資料")
                    return False
                
                print(f"✅ {os.path.basename(csv_file)} 驗證通過 ({len(df)} 筆資料)")
                
            except Exception as e:
                print(f"❌ 驗證 {csv_file} 時發生錯誤: {e}")
                return False
        
        return True

# ==============================================================================
# 🏢 5. Milvus 管理器
# ==============================================================================
class MilvusManager:
    """Milvus 管理器"""
    
    def __init__(self, config):
        self.config = config
    
    def create_milvus_collection_if_not_exists(self):
        """建立 Milvus Collection（如果不存在）"""
        if utility.has_collection(self.config.COLLECTION_NAME):
            print(f"✅ Collection '{self.config.COLLECTION_NAME}' 已存在")
            return Collection(self.config.COLLECTION_NAME)
        
        print(f"🏗️ Collection '{self.config.COLLECTION_NAME}' 不存在，開始建立...")
        fields = [
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128, is_primary=True),
            FieldSchema(name="original_text", dtype=DataType.VARCHAR, max_length=8192), 
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.config.EMBEDDING_DIM),
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
        collection = Collection(name=self.config.COLLECTION_NAME, schema=schema)
        
        print("🔍 正在為 embedding 欄位建立索引...")
        index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
        collection.create_index(field_name="embedding", index_params=index_params)
        print(f"✅ Collection '{self.config.COLLECTION_NAME}' 與索引建立完成！")
        return collection
    
    def write_to_milvus(self, chunks, embeddings):
        """寫入資料到 Milvus"""
        print(f"\n🗄️ 正在連線到 Milvus ({self.config.MILVUS_HOST}:{self.config.MILVUS_PORT})...")
        
        try:
            connections.connect("default", host=self.config.MILVUS_HOST, port=self.config.MILVUS_PORT)
            print("✅ Milvus 連線成功")
            
            collection = self.create_milvus_collection_if_not_exists()
            existing_count = collection.num_entities
            
            if existing_count > 0: 
                print(f"⚠️ Collection 中已有 {existing_count} 筆資料")
                user_input = input("是否要清空現有資料並重新匯入？(y/N): ")
                if user_input.lower() == 'y':
                    collection.drop()
                    print("🗑️ 已清空現有資料")
                    collection = self.create_milvus_collection_if_not_exists()
                else:
                    print("ℹ️ 跳過資料匯入")
                    return True
            
            # 分批上傳資料
            total_batches = (len(chunks) + self.config.INSERT_BATCH_SIZE - 1) // self.config.INSERT_BATCH_SIZE
            print(f"📤 開始上傳資料 ({total_batches} 個批次)...")
            
            for i in range(0, len(chunks), self.config.INSERT_BATCH_SIZE):
                batch_num = i // self.config.INSERT_BATCH_SIZE + 1
                batch_end = min(i + self.config.INSERT_BATCH_SIZE, len(chunks))
                
                print(f"  📦 上傳批次 {batch_num}/{total_batches} (第 {i+1}-{batch_end} 筆資料)...")
                
                data_to_insert = [
                    [chunk['chunk_id'] for chunk in chunks[i:batch_end]],
                    [chunk['original_text'] for chunk in chunks[i:batch_end]],
                    embeddings[i:batch_end].tolist(),
                    [chunk['job_id'] for chunk in chunks[i:batch_end]],
                    [chunk['job_title'] for chunk in chunks[i:batch_end]],
                    [chunk['company_name'] for chunk in chunks[i:batch_end]],
                    [chunk['location'] for chunk in chunks[i:batch_end]],
                    [chunk['experience_req'] for chunk in chunks[i:batch_end]],
                    [chunk['salary_min'] for chunk in chunks[i:batch_end]],
                    [chunk['salary_max'] for chunk in chunks[i:batch_end]],
                    [chunk['job_url'] for chunk in chunks[i:batch_end]],
                    [chunk.get('source_file', 'unknown') for chunk in chunks[i:batch_end]]
                ]
                collection.insert(data_to_insert)
            
            collection.flush()
            final_count = collection.num_entities
            print(f"\n🎉 資料上傳完成！")
            print(f"  - Collection: {self.config.COLLECTION_NAME}")
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

# ==============================================================================
# 📁 6. 資料處理器
# ==============================================================================
class DataProcessor:
    """資料處理器"""
    
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def get_csv_files_from_directory(self, directory_path):
        """掃描指定資料夾中的所有 CSV 檔案"""
        csv_files = []
        if os.path.exists(directory_path):
            pattern = os.path.join(directory_path, "*.csv")
            all_files = glob.glob(pattern)
            for file in all_files:
                if not file.endswith(':Zone.Identifier'):
                    csv_files.append(file)
        return sorted(csv_files)
    
    def process_csv_files(self, csv_files):
        """處理多個 CSV 檔案"""
        all_chunks = []
        total_rows = 0
        
        for csv_file in csv_files:
            print(f"\n📄 正在處理檔案: {os.path.basename(csv_file)}")
            try:
                df = pd.read_csv(csv_file)
                print(f"✅ 成功讀取 {len(df)} 筆資料")
                
                # 資料清理
                for col in self.config.TEXT_FIELDS_TO_COMBINE + ["上班地點", "工作經歷要求", "職缺連結"]: 
                    if col in df.columns:
                        df[col] = df[col].fillna('')
                
                for col in ["薪資下限", "薪資上限"]: 
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                
                # 文字組合
                text_fields = [col for col in self.config.TEXT_FIELDS_TO_COMBINE if col in df.columns]
                df['text_to_embed'] = df[text_fields].apply(
                    lambda x: "\n".join(f"{col}: {val}" for col, val in x.items() if val), axis=1
                )
                
                # 文字切割
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.config.CHUNK_SIZE, 
                    chunk_overlap=self.config.CHUNK_OVERLAP
                )
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
    
    def get_openai_embeddings(self, texts):
        """使用 OpenAI API 生成 embeddings"""
        all_embeddings = []
        total_batches = (len(texts) + self.config.EMBEDDING_BATCH_SIZE - 1) // self.config.EMBEDDING_BATCH_SIZE
        
        for i in range(0, len(texts), self.config.EMBEDDING_BATCH_SIZE):
            batch_num = i // self.config.EMBEDDING_BATCH_SIZE + 1
            batch = texts[i:i + self.config.EMBEDDING_BATCH_SIZE]
            
            try:
                print(f"🤖 正在處理批次 {batch_num}/{total_batches} ({len(batch)} 個文字區塊)...")
                response = self.client.embeddings.create(input=batch, model=self.config.MODEL_NAME)
                embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(embeddings)
                time.sleep(1)  # 避免 API 限制
            except Exception as e:
                print(f"❌ OpenAI API 呼叫失敗: {e}。等待 {self.config.API_RETRY_DELAY} 秒後重試...")
                time.sleep(self.config.API_RETRY_DELAY)
                # 重試一次
                try:
                    response = self.client.embeddings.create(input=batch, model=self.config.MODEL_NAME)
                    embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(embeddings)
                except Exception as retry_e:
                    print(f"❌ 重試失敗: {retry_e}")
                    return None
        
        return all_embeddings
    
    def load_cache_data(self):
        """載入快取資料"""
        print(f"📂 載入快取檔案...")
        try:
            with open(self.config.CHUNKS_PATH, 'rb') as f: 
                chunks = pickle.load(f)
            embeddings = np.load(self.config.EMBEDDINGS_PATH)
            print(f"✅ 成功載入 {len(chunks)} 個 chunks 和 {len(embeddings)} 個 embeddings")
            return chunks, embeddings
        except Exception as e:
            print(f"❌ 載入快取檔案失敗: {e}")
            return None, None
    
    def save_cache_data(self, chunks, embeddings, csv_files_info):
        """儲存快取資料"""
        print("\n💾 正在儲存快取檔案...")
        os.makedirs(os.path.dirname(self.config.CHUNKS_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(self.config.EMBEDDINGS_PATH), exist_ok=True)
        
        with open(self.config.CHUNKS_PATH, 'wb') as f: 
            pickle.dump(chunks, f)
        print(f"✅ Chunks 已儲存至 '{self.config.CHUNKS_PATH}'")
        
        np.save(self.config.EMBEDDINGS_PATH, embeddings)
        print(f"✅ Embeddings 已儲存至 '{self.config.EMBEDDINGS_PATH}'")
        
        # 儲存元資料
        consistency_checker = DataConsistencyChecker(self.config)
        consistency_checker.save_cache_metadata(csv_files_info, len(chunks), len(embeddings))

# ==============================================================================
# 🎯 7. 主控制器
# ==============================================================================
class JobDataManager:
    """職缺資料管理器 - 主控制器"""
    
    def __init__(self):
        self.config = Config()
        self.consistency_checker = DataConsistencyChecker(self.config)
        self.connection_checker = ConnectionChecker(self.config)
        self.data_validator = DataValidator(self.config)
        self.milvus_manager = MilvusManager(self.config)
        self.data_processor = DataProcessor(self.config)
    
    def run(self):
        """執行主要流程"""
        print("🚀 開始優化版職缺搜尋資料庫設定...")
        self.config.print_config()
        
        # 1. 提前檢查連接
        print("\n" + "="*50)
        print("🔍 步驟 1: 檢查系統連接")
        print("="*50)
        
        if not self.connection_checker.check_milvus_connection():
            print("❌ Milvus 連接失敗，程式終止")
            return False
        
        if not self.connection_checker.check_openai_connection():
            print("❌ OpenAI API 連接失敗，程式終止")
            return False
        
        # 2. 檢查資料一致性
        print("\n" + "="*50)
        print("🔍 步驟 2: 檢查資料一致性")
        print("="*50)
        
        chunks = None
        embeddings = None
        
        if self.consistency_checker.is_cache_valid():
            # 載入並驗證快取
            chunks, embeddings = self.data_processor.load_cache_data()
            if chunks is not None and embeddings is not None:
                if self.data_validator.validate_cache_data(chunks, embeddings):
                    print("✅ 使用快取資料")
                else:
                    print("❌ 快取資料驗證失敗，將重新處理")
                    chunks = None
                    embeddings = None
        
        # 3. 如果沒有有效快取，重新處理資料
        if not chunks or embeddings is None:
            print("\n" + "="*50)
            print("🔍 步驟 3: 處理原始資料")
            print("="*50)
            
            # 檢查 CSV 檔案
            csv_files = self.data_processor.get_csv_files_from_directory(self.config.JOBS_DIR)
            if not csv_files:
                print(f"❌ 錯誤：在 '{self.config.JOBS_DIR}' 資料夾中找不到任何 CSV 檔案")
                return False
            
            print(f"📁 找到 {len(csv_files)} 個 CSV 檔案:")
            for file in csv_files:
                print(f"  - {os.path.basename(file)}")
            
            # 驗證 CSV 資料
            if not self.data_validator.validate_csv_data(csv_files):
                print("❌ CSV 資料驗證失敗")
                return False
            
            # 處理 CSV 檔案
            chunks = self.data_processor.process_csv_files(csv_files)
            if not chunks:
                print("❌ 沒有產生任何文字區塊，程式結束")
                return False
            
            # 向量化
            print("\n🤖 正在使用 OpenAI API 進行向量化...")
            start_time = time.time()
            chunk_texts = [chunk['original_text'] for chunk in chunks]
            embeddings_list = self.data_processor.get_openai_embeddings(chunk_texts)
            
            if not embeddings_list or len(embeddings_list) != len(chunks):
                print("❌ 向量化失敗，程式終止")
                return False
            
            embeddings = np.array(embeddings_list)
            print(f"✅ 向量化完成！耗時 {time.time() - start_time:.2f} 秒")
            
            # 儲存快取
            csv_files_info = self.consistency_checker.get_csv_files_info()
            self.data_processor.save_cache_data(chunks, embeddings, csv_files_info)
        
        # 4. 寫入 Milvus
        print("\n" + "="*50)
        print("🔍 步驟 4: 寫入 Milvus")
        print("="*50)
        
        success = self.milvus_manager.write_to_milvus(chunks, embeddings)
        
        if success:
            print("\n" + "="*60)
            print("✅ 優化版資料庫設定完成！")
            print("="*60)
            return True
        else:
            print("\n" + "="*60)
            print("❌ 資料庫設定失敗！")
            print("="*60)
            return False

# ==============================================================================
# 🚀 8. 主程式入口
# ==============================================================================
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
    print("🚀 FastMCP-FastAgent 優化版職缺搜尋資料庫設定")
    print("=" * 60)
    
    try:
        # 執行主要設定流程
        manager = JobDataManager()
        if manager.run():
            # 測試搜尋功能
            if test_search():
                print("🎯 系統已準備就緒，可以開始使用職缺搜尋功能！")
            else:
                print("⚠️ 搜尋功能測試失敗，請檢查配置")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"❌ 程式執行失敗: {e}")
        sys.exit(1)
    
    print("=" * 60)
