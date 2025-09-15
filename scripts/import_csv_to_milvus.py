#!/usr/bin/env python3
"""
CSV 檔案匯入 Milvus 向量資料庫腳本
專門處理 Jobs_merged_output_0730.csv 檔案
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
import time
import numpy as np

# 載入環境變數
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv 未安裝，直接讀取環境變數")

class JobCSVImporter:
    """職缺 CSV 匯入器"""
    
    def __init__(self):
        # Milvus 設定
        self.milvus_host = os.getenv("MILVUS_HOST", "localhost")
        self.milvus_port = os.getenv("MILVUS_PORT", "19530")
        self.collection_name = "job_postings_openai"
        
        # OpenAI 設定
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("❌ 錯誤：請設定 OPENAI_API_KEY 環境變數")
        
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dim = 1536
        
        # 處理設定
        self.batch_size = 10  # 向量化批次大小
        self.insert_batch_size = 100  # 插入批次大小
        self.max_text_length = 10000  # 最大文字長度
        
        # CSV 檔案路徑
        self.csv_file_path = r"/app/data/213/Jobs_merged_output_0730.csv"
        
    def connect_milvus(self) -> bool:
        """連接到 Milvus"""
        try:
            connections.connect("default", host=self.milvus_host, port=self.milvus_port)
            print(f"✅ Milvus 連線成功 ({self.milvus_host}:{self.milvus_port})")
            return True
        except Exception as e:
            print(f"❌ Milvus 連線失敗: {e}")
            return False
    
    def create_collection_schema(self):
        """創建 Collection Schema"""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="job_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="company", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="location", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=8000),
            FieldSchema(name="requirements", dtype=DataType.VARCHAR, max_length=8000),  # 增加到 8000
            FieldSchema(name="skills", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(name="salary_min", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="salary_max", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="url", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="full_text", dtype=DataType.VARCHAR, max_length=self.max_text_length),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
        ]
        
        schema = CollectionSchema(fields, "Job postings with OpenAI embeddings")
        return schema
    
    def truncate_string(self, text: str, max_length: int) -> str:
        """截斷字串到指定長度"""
        if not text:
            return ""
        text = str(text).strip()
        if len(text) <= max_length:
            return text
        return text[:max_length]
    
    def create_collection_if_not_exists(self):
        """創建 Collection（如果不存在）"""
        if not self.connect_milvus():
            return None
            
        try:
            if utility.has_collection(self.collection_name):
                collection = Collection(self.collection_name)
                existing_count = collection.num_entities
                
                if existing_count > 0:
                    print(f"⚠️ Collection '{self.collection_name}' 已存在，包含 {existing_count} 筆資料")
                    user_input = input("是否要清空現有資料並重新匯入？(y/N): ").strip().lower()
                    if user_input == 'y':
                        collection.drop()
                        print("🗑️ 已清空現有資料")
                    else:
                        print("ℹ️ 取消匯入，保留現有資料")
                        return None
            
            # 創建新的 Collection
            schema = self.create_collection_schema()
            collection = Collection(name=self.collection_name, schema=schema)
            
            # 創建索引
            print("🔍 正在創建向量索引...")
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            print(f"✅ Collection '{self.collection_name}' 創建完成！")
            
            return collection
            
        except Exception as e:
            print(f"❌ 創建 Collection 失敗: {e}")
            return None
    
    def load_and_clean_csv(self):
        """載入並清理 CSV 資料"""
        print(f"📁 載入 CSV 檔案: {self.csv_file_path}")
        
        try:
            # 讀取 CSV
            df = pd.read_csv(self.csv_file_path)
            print(f"✅ 成功載入 {len(df)} 筆資料")
            
            # 顯示欄位名稱
            print("📊 CSV 欄位:")
            for i, col in enumerate(df.columns):
                print(f"  {i+1:2d}. {col}")
            
            # 基本清理
            print("🧹 清理資料...")
            
            # 填補空值
            df = df.fillna("")
            
            # 移除完全空白的行
            df = df[df.astype(str).apply(lambda x: x.str.strip()).ne("").any(axis=1)]
            
            print(f"✅ 清理後剩餘 {len(df)} 筆資料")
            return df
            
        except Exception as e:
            print(f"❌ 載入 CSV 失敗: {e}")
            return None
    
    def prepare_job_data(self, df):
        """準備職缺資料"""
        print("🔧 準備職缺資料...")
        
        job_data = []
        
        for idx, row in df.iterrows():
            try:
                # 組合完整文字內容用於向量化
                text_parts = []
                
                # 基本資訊
                if row.get("職缺名稱", "").strip():
                    text_parts.append(f"職缺: {row['職缺名稱']}")
                
                if row.get("公司名稱", "").strip():
                    text_parts.append(f"公司: {row['公司名稱']}")
                
                if row.get("上班地點", "").strip():
                    text_parts.append(f"地點: {row['上班地點']}")
                
                # 職缺描述
                if row.get("職缺描述", "").strip():
                    text_parts.append(f"描述: {row['職缺描述']}")
                
                # 職務需求
                if row.get("職務需求", "").strip():
                    text_parts.append(f"需求: {row['職務需求']}")
                
                # 技能要求
                if row.get("擅長工具", "").strip():
                    text_parts.append(f"工具: {row['擅長工具']}")
                
                if row.get("工作技能", "").strip():
                    text_parts.append(f"技能: {row['工作技能']}")
                
                # 組合完整文字
                full_text = " | ".join(text_parts)
                
                # 限制文字長度
                if len(full_text) > self.max_text_length:
                    full_text = full_text[:self.max_text_length]
                
                # 如果文字太短，跳過
                if len(full_text.strip()) < 50:
                    continue
                
                job_data.append({
                    "job_id": self.truncate_string(str(row.get("job_id", f"job_{idx}")), 100),
                    "source": self.truncate_string(str(row.get("資料來源", "")).strip() or "unknown", 50),
                    "title": self.truncate_string(str(row.get("職缺名稱", "")).strip() or "未知職缺", 500),
                    "company": self.truncate_string(str(row.get("公司名稱", "")).strip() or "未知公司", 500),
                    "location": self.truncate_string(str(row.get("上班地點", "")).strip() or "未知地點", 200),
                    "description": self.truncate_string(str(row.get("職缺描述", "")).strip(), 8000),
                    "requirements": self.truncate_string(str(row.get("職務需求", "")).strip(), 8000),
                    "skills": self.truncate_string(f"{row.get('擅長工具', '')} | {row.get('工作技能', '')}".strip(), 2000),
                    "salary_min": self.truncate_string(str(row.get("薪資下限", "")).strip(), 50),
                    "salary_max": self.truncate_string(str(row.get("薪資上限", "")).strip(), 50),
                    "url": self.truncate_string(str(row.get("職缺連結", "")).strip(), 1000),
                    "full_text": self.truncate_string(full_text, self.max_text_length)
                })
                
            except Exception as e:
                print(f"⚠️ 處理第 {idx} 行資料時發生錯誤: {e}")
                continue
        
        print(f"✅ 準備完成 {len(job_data)} 筆有效資料")
        return job_data
    
    def generate_embeddings(self, job_data):
        """生成向量嵌入"""
        print("🤖 開始生成向量嵌入...")
        
        embeddings = []
        total_batches = (len(job_data) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(job_data), self.batch_size):
            batch = job_data[i:i + self.batch_size]
            batch_texts = [item["full_text"] for item in batch]
            
            try:
                response = self.openai_client.embeddings.create(
                    input=batch_texts,
                    model=self.embedding_model
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
                current_batch = (i // self.batch_size) + 1
                print(f"📊 進度: {current_batch}/{total_batches} 批次 ({len(embeddings)}/{len(job_data)} 筆)")
                
                # API 限制延遲
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ 批次 {current_batch} 向量化失敗: {e}")
                # 填充空向量以保持索引一致
                empty_embedding = [0.0] * self.embedding_dim
                for _ in batch:
                    embeddings.append(empty_embedding)
        
        print(f"✅ 向量生成完成: {len(embeddings)} 個向量")
        return embeddings
    
    def insert_to_milvus(self, job_data, embeddings):
        """插入資料到 Milvus"""
        print("💾 開始插入資料到 Milvus...")
        
        # 驗證資料
        if not job_data or not embeddings:
            print("❌ 錯誤：job_data 或 embeddings 為空")
            return False
        
        if len(job_data) != len(embeddings):
            print(f"❌ 錯誤：資料數量不匹配 - job_data: {len(job_data)}, embeddings: {len(embeddings)}")
            return False
        
        # 驗證第一筆資料的結構
        first_job = job_data[0]
        required_fields = ["job_id", "source", "title", "company", "location", "description", 
                         "requirements", "skills", "salary_min", "salary_max", "url", "full_text"]
        
        missing_fields = [field for field in required_fields if field not in first_job]
        if missing_fields:
            print(f"❌ 錯誤：缺少必要欄位: {missing_fields}")
            return False
        
        # 驗證 embedding 維度
        if len(embeddings[0]) != self.embedding_dim:
            print(f"❌ 錯誤：embedding 維度不匹配 - 預期: {self.embedding_dim}, 實際: {len(embeddings[0])}")
            return False
        
        print("✅ 資料驗證通過")
        
        collection = self.create_collection_if_not_exists()
        if not collection:
            return False
        
        try:
            # 準備插入資料
            insert_data = []
            for i, (job, embedding) in enumerate(zip(job_data, embeddings)):
                insert_data.append([
                    job["job_id"],
                    job["source"],
                    job["title"],
                    job["company"],
                    job["location"],
                    job["description"],
                    job["requirements"],
                    job["skills"],
                    job["salary_min"],
                    job["salary_max"],
                    job["url"],
                    job["full_text"],
                    embedding
                ])
            
            # 分批插入
            total_batches = (len(insert_data) + self.insert_batch_size - 1) // self.insert_batch_size
            
            for i in range(0, len(insert_data), self.insert_batch_size):
                batch_data = insert_data[i:i + self.insert_batch_size]
                
                try:
                    # 轉置資料格式以符合 Milvus 要求
                    batch_formatted = list(map(list, zip(*batch_data)))
                    
                    # 明確指定要插入的欄位名稱（跳過 id 欄位）
                    field_names = ["job_id", "source", "title", "company", "location", "description", 
                                 "requirements", "skills", "salary_min", "salary_max", "url", "full_text", "embedding"]
                    
                    collection.insert(batch_formatted, field_names)
                    
                    current_batch = (i // self.insert_batch_size) + 1
                    print(f"📤 插入進度: {current_batch}/{total_batches} 批次 ({len(batch_data)} 筆)")
                    
                except Exception as batch_error:
                    current_batch = (i // self.insert_batch_size) + 1
                    print(f"❌ 批次 {current_batch} 插入失敗: {batch_error}")
                    print(f"   批次資料範例: {batch_data[0] if batch_data else 'N/A'}")
                    print(f"   批次資料長度: {len(batch_data)}")
                    continue
            
            # 確保資料寫入
            collection.flush()
            print("✅ 資料插入完成，正在載入索引...")
            
            # 載入 Collection
            collection.load()
            
            # 檢查最終資料數量
            final_count = collection.num_entities
            print(f"🎉 匯入完成！Milvus 中共有 {final_count} 筆職缺資料")
            
            return True
            
        except Exception as e:
            print(f"❌ 插入資料失敗: {e}")
            return False
    
    def run_import(self):
        """執行完整匯入流程"""
        print("🚀 開始 CSV 匯入 Milvus 流程")
        print("=" * 50)
        
        try:
            # 1. 載入 CSV
            df = self.load_and_clean_csv()
            if df is None:
                return False
            
            # 2. 準備資料
            job_data = self.prepare_job_data(df)
            if not job_data:
                print("❌ 沒有有效的職缺資料")
                return False
            
            # 3. 生成向量
            embeddings = self.generate_embeddings(job_data)
            if len(embeddings) != len(job_data):
                print("❌ 向量數量與資料數量不符")
                return False
            
            # 4. 插入 Milvus
            success = self.insert_to_milvus(job_data, embeddings)
            
            if success:
                print("\n🎉 CSV 匯入完成！")
                return True
            else:
                print("\n❌ CSV 匯入失敗")
                return False
                
        except Exception as e:
            print(f"❌ 匯入過程發生錯誤: {e}")
            return False

def main():
    """主函數"""
    print("🔧 CSV 到 Milvus 匯入工具")
    print("=" * 50)
    
    try:
        importer = JobCSVImporter()
        success = importer.run_import()
        
        if success:
            print("\n✅ 匯入成功完成！")
            sys.exit(0)
        else:
            print("\n❌ 匯入失敗")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ 使用者中斷操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程式執行錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
