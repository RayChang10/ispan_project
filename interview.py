"""
面試資料匯入 MongoDB 程式
將 interviewdata 資料夾中的 CSV 檔案匯入到 MongoDB 資料庫
"""

import csv
import logging
import os
from typing import Any, Dict, List

from pymongo import MongoClient
from pymongo.errors import BulkWriteError, ConnectionFailure

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class InterviewDataImporter:
    """面試資料匯入器"""

    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        db_name: str = "interview_db",
    ):
        """
        初始化匯入器

        Args:
            mongo_uri: MongoDB 連接 URI
            db_name: 資料庫名稱
        """
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None

    def connect_to_mongodb(self) -> bool:
        """連接到 MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri)
            # 測試連接
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]
            logger.info(f"✅ 成功連接到 MongoDB: {self.mongo_uri}")
            logger.info(f"📊 使用資料庫: {self.db_name}")
            return True
        except ConnectionFailure as e:
            logger.info(f"ℹ️  MongoDB 未運行，資料庫功能將不可用（不影響主要功能）")
            return False
        except Exception as e:
            logger.error(f"❌ 連接錯誤: {e}")
            return False

    def disconnect_from_mongodb(self):
        """斷開 MongoDB 連接"""
        if self.client:
            self.client.close()
            logger.info("🔌 已斷開 MongoDB 連接")

    def get_csv_files(self, data_dir: str = "interview_csv") -> List[str]:
        """
        獲取指定目錄中的所有 CSV 檔案

        Args:
            data_dir: 資料目錄路徑

        Returns:
            CSV 檔案路徑列表
        """
        csv_files = []
        if not os.path.exists(data_dir):
            logger.error(f"❌ 目錄不存在: {data_dir}")
            return csv_files

        for filename in os.listdir(data_dir):
            if filename.endswith(".csv"):
                file_path = os.path.join(data_dir, filename)
                csv_files.append(file_path)
                logger.info(f"📁 發現 CSV 檔案: {filename}")

        return csv_files

    def get_collection_name(self, csv_file_path: str) -> str:
        """
        根據 CSV 檔案名稱生成 MongoDB 集合名稱

        Args:
            csv_file_path: CSV 檔案路徑

        Returns:
            MongoDB 集合名稱
        """
        # 取得檔案名稱（不含副檔名）
        filename = os.path.basename(csv_file_path)
        collection_name = os.path.splitext(filename)[0]

        # 將檔案名稱轉換為有效的集合名稱
        # MongoDB 集合名稱不能包含特殊字符，只能包含字母、數字、底線
        collection_name = "".join(c for c in collection_name if c.isalnum() or c == "_")

        # 確保集合名稱不以數字開頭
        if collection_name and collection_name[0].isdigit():
            collection_name = f"collection_{collection_name}"

        return collection_name

    def read_csv_file(self, csv_file_path: str) -> List[Dict[str, Any]]:
        """
        讀取 CSV 檔案並轉換為字典列表

        Args:
            csv_file_path: CSV 檔案路徑

        Returns:
            字典列表
        """
        data = []

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                # 嘗試自動檢測編碼
                content = file.read()
                file.seek(0)

                # 使用 csv.DictReader 讀取
                reader = csv.DictReader(file)

                for row_num, row in enumerate(
                    reader, start=2
                ):  # 從第2行開始（跳過標題）
                    # 清理資料：移除空值、處理特殊字符
                    cleaned_row = {}
                    for key, value in row.items():
                        if value is not None and value.strip():
                            # 清理欄位名稱
                            clean_key = key.strip()
                            # 清理值
                            clean_value = value.strip()
                            cleaned_row[clean_key] = clean_value

                    if cleaned_row:  # 只添加非空行
                        # 添加來源檔案資訊
                        cleaned_row["_source_file"] = os.path.basename(csv_file_path)
                        cleaned_row["_row_number"] = row_num
                        data.append(cleaned_row)

                logger.info(
                    f"📖 成功讀取 {len(data)} 筆資料從 {os.path.basename(csv_file_path)}"
                )

        except UnicodeDecodeError:
            # 如果 UTF-8 失敗，嘗試其他編碼
            try:
                with open(csv_file_path, "r", encoding="gbk") as file:
                    reader = csv.DictReader(file)
                    for row_num, row in enumerate(reader, start=2):
                        cleaned_row = {}
                        for key, value in row.items():
                            if value is not None and value.strip():
                                clean_key = key.strip()
                                clean_value = value.strip()
                                cleaned_row[clean_key] = clean_value

                        if cleaned_row:
                            cleaned_row["_source_file"] = os.path.basename(
                                csv_file_path
                            )
                            cleaned_row["_row_number"] = row_num
                            data.append(cleaned_row)

                logger.info(
                    f"📖 成功讀取 {len(data)} 筆資料從 {os.path.basename(csv_file_path)} (使用 GBK 編碼)"
                )

            except Exception as e:
                logger.error(f"❌ 讀取檔案失敗 {csv_file_path}: {e}")

        except Exception as e:
            logger.error(f"❌ 讀取檔案失敗 {csv_file_path}: {e}")

        return data

    def import_to_mongodb(
        self, collection_name: str, data: List[Dict[str, Any]]
    ) -> bool:
        """
        將資料匯入到 MongoDB 集合

        Args:
            collection_name: 集合名稱
            data: 要匯入的資料

        Returns:
            是否成功
        """
        if not data:
            logger.warning(f"⚠️ 沒有資料要匯入到集合 {collection_name}")
            return True

        if self.db is None:
            logger.error("❌ 資料庫連接未建立")
            return False

        try:
            collection = self.db[collection_name]

            # 檢查集合是否已存在資料
            existing_count = collection.count_documents({})
            if existing_count > 0:
                logger.warning(
                    f"⚠️ 集合 {collection_name} 已存在 {existing_count} 筆資料"
                )

                # 詢問是否要清空集合
                response = (
                    input(f"是否要清空集合 {collection_name} 並重新匯入？(y/N): ")
                    .strip()
                    .lower()
                )
                if response == "y":
                    collection.delete_many({})
                    logger.info(f"🗑️ 已清空集合 {collection_name}")
                else:
                    logger.info(f"⏭️ 跳過集合 {collection_name}")
                    return True

            # 批量插入資料
            result = collection.insert_many(data)
            logger.info(
                f"✅ 成功匯入 {len(result.inserted_ids)} 筆資料到集合 {collection_name}"
            )

            # 創建索引以提高查詢效能
            self.create_indexes(collection)

            return True

        except BulkWriteError as e:
            logger.error(f"❌ 批量寫入錯誤 {collection_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 匯入錯誤 {collection_name}: {e}")
            return False

    def create_indexes(self, collection):
        """為集合創建索引"""
        try:
            # 為常用查詢欄位創建索引
            collection.create_index("_source_file")
            collection.create_index("_row_number")

            # 為問題和答案欄位創建文字索引（如果存在）
            try:
                collection.create_index([("問題", "text"), ("答案", "text")])
                collection.create_index([("Question", "text"), ("Answer", "text")])
                collection.create_index([("題目", "text")])
            except Exception:
                # 如果欄位不存在，忽略錯誤
                pass

            logger.info(f"🔍 已為集合 {collection.name} 創建索引")

        except Exception as e:
            logger.warning(f"⚠️ 創建索引失敗: {e}")

    def import_all_csv_files(self, data_dir: str = "interview_csv") -> Dict[str, bool]:
        """
        匯入所有 CSV 檔案

        Args:
            data_dir: 資料目錄路徑

        Returns:
            匯入結果字典
        """
        results = {}

        # 連接到 MongoDB
        if not self.connect_to_mongodb():
            return results

        try:
            # 獲取所有 CSV 檔案
            csv_files = self.get_csv_files(data_dir)

            if not csv_files:
                logger.warning("⚠️ 沒有找到 CSV 檔案")
                return results

            logger.info(f"🚀 開始匯入 {len(csv_files)} 個 CSV 檔案")

            # 逐一處理每個 CSV 檔案
            for csv_file in csv_files:
                try:
                    # 生成集合名稱
                    collection_name = self.get_collection_name(csv_file)
                    logger.info(f"📋 處理集合: {collection_name}")

                    # 讀取 CSV 檔案
                    data = self.read_csv_file(csv_file)

                    if data:
                        # 匯入到 MongoDB
                        success = self.import_to_mongodb(collection_name, data)
                        results[collection_name] = success
                    else:
                        logger.warning(f"⚠️ 檔案 {csv_file} 沒有有效資料")
                        results[collection_name] = False

                except Exception as e:
                    logger.error(f"❌ 處理檔案 {csv_file} 時發生錯誤: {e}")
                    collection_name = self.get_collection_name(csv_file)
                    results[collection_name] = False

            # 顯示匯入統計
            self.show_import_statistics(results)

        finally:
            # 斷開連接
            self.disconnect_from_mongodb()

        return results

    def show_import_statistics(self, results: Dict[str, bool]):
        """顯示匯入統計"""
        total_files = len(results)
        successful_imports = sum(1 for success in results.values() if success)
        failed_imports = total_files - successful_imports

        print("\n" + "=" * 50)
        print("📊 匯入統計")
        print("=" * 50)
        print(f"📁 總檔案數: {total_files}")
        print(f"✅ 成功匯入: {successful_imports}")
        print(f"❌ 失敗匯入: {failed_imports}")
        print(f"📈 成功率: {(successful_imports/total_files)*100:.1f}%")

        if failed_imports > 0:
            print("\n❌ 失敗的集合:")
            for collection_name, success in results.items():
                if not success:
                    print(f"   - {collection_name}")

        print("=" * 50)

    def list_collections(self):
        """列出所有集合"""
        if not self.connect_to_mongodb():
            return

        if self.db is None:
            logger.error("❌ 資料庫連接未建立")
            return

        try:
            collections = self.db.list_collection_names()
            print(f"\n📋 資料庫 {self.db_name} 中的集合:")
            for i, collection in enumerate(collections, 1):
                count = self.db[collection].count_documents({})
                print(f"   {i}. {collection} ({count} 筆資料)")

        finally:
            self.disconnect_from_mongodb()


def main():
    """主程式"""
    print("🚀 面試資料 MongoDB 匯入程式")
    print("=" * 50)

    # 創建匯入器實例
    importer = InterviewDataImporter()

    # 顯示選項
    print("\n請選擇操作:")
    print("1. 匯入所有 CSV 檔案")
    print("2. 列出現有集合")
    print("3. 退出")

    while True:
        choice = input("\n請輸入選項 (1-3): ").strip()

        if choice == "1":
            print("\n開始匯入 CSV 檔案...")
            results = importer.import_all_csv_files()

            if results:
                print("\n✅ 匯入完成！")
            else:
                print("\n❌ 匯入失敗！")

        elif choice == "2":
            importer.list_collections()

        elif choice == "3":
            print("👋 再見！")
            break

        else:
            print("❌ 無效選項，請重新輸入")


if __name__ == "__main__":
    main()
