"""
面試資料匯入 MongoDB 程式
將 interviewdata 資料夾中的 CSV 檔案匯入到 MongoDB 資料庫
"""

import csv
import logging
import os
from typing import Any, Dict, List, Optional

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
        mongo_uri: Optional[str] = None,
        db_name: Optional[str] = None,
    ):
        """
        初始化匯入器

        Args:
            mongo_uri: MongoDB 連接 URI
            db_name: 資料庫名稱
        """
        # 允許以參數或環境變數指定，最後退回預設值
        # 在 Docker 環境中使用 mongo 容器名稱，在主機使用 localhost
        # 檢查是否在 Docker 環境中運行
        if os.path.exists('/.dockerenv'):
            # 在 Docker 容器內運行
            default_uri = "mongodb://admin:changeme@mongo:27017/?authSource=admin"
        else:
            # 在主機上運行，連接到 Docker 的 MongoDB
            default_uri = "mongodb://admin:changeme@localhost:27017/?authSource=admin"
            
        self.mongo_uri = mongo_uri or os.getenv("MONGO_URI", default_uri)
        # 面試問題使用 interview_db，履歷使用 resume_db
        self.db_name = db_name or os.getenv("MONGO_DB_NAME", "interview_db")
        self.client = None
        self.db = None
        
        # 記錄連接資訊
        logger.info(f"🔗 MongoDB URI: {self.mongo_uri}")
        logger.info(f"📊 目標資料庫: {self.db_name}")

    def connect_to_mongodb(self) -> bool:
        """連接到 MongoDB"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 嘗試連接 MongoDB (第 {attempt + 1} 次)...")
                
                # 設定連接選項
                connection_options = {
                    'serverSelectionTimeoutMS': 5000,  # 5秒超時
                    'connectTimeoutMS': 10000,         # 10秒連接超時
                    'socketTimeoutMS': 10000,          # 10秒socket超時
                    'maxPoolSize': 10,                 # 最大連接池大小
                    'retryWrites': True,               # 啟用重試寫入
                }
                
                self.client = MongoClient(self.mongo_uri, **connection_options)
                
                # 測試連接
                self.client.admin.command("ping")
                self.db = self.client[self.db_name]
                
                # 測試資料庫訪問
                self.db.list_collection_names()
                
                logger.info("✅ 成功連接到 MongoDB 伺服器")
                logger.info(f"📊 使用資料庫: {self.db_name}")
                logger.info(f"🔗 連接字串: {self.mongo_uri.split('@')[1] if '@' in self.mongo_uri else 'local'}")  # 隱藏密碼
                return True
                
            except ConnectionFailure as e:
                logger.warning(f"⚠️  連接失敗 (第 {attempt + 1} 次): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ {retry_delay} 秒後重試...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指數退避
                else:
                    logger.error("❌ MongoDB 連接失敗，請檢查:")
                    logger.error("   1. MongoDB 服務是否正在運行")
                    logger.error("   2. 連接字串是否正確")
                    logger.error("   3. 網路連接是否正常")
                    if "localhost" in self.mongo_uri:
                        logger.error("   4. 如果使用 Docker，請確保 MongoDB 容器正在運行")
                        logger.error("   5. 使用 'docker-compose ps' 檢查容器狀態")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ 連接錯誤: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ {retry_delay} 秒後重試...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    return False
                    
        return False

    def setup_environment_variables(self):
        """設定環境變數"""
        env_vars = {
            'MONGO_URI': self.mongo_uri,
            'MONGO_DB_NAME': self.db_name,
            'DOCKER_ENV': 'true' if os.path.exists('/.dockerenv') else 'false'
        }
        
        print("\n🔧 環境變數設定:")
        for key, value in env_vars.items():
            print(f"   {key}: {value}")
            
        # 檢查是否有 .env 檔案
        env_file_path = '.env'
        if os.path.exists(env_file_path):
            print(f"\n📁 發現 .env 檔案: {env_file_path}")
            try:
                with open(env_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'MONGO_URI' in content or 'MONGO_DB_NAME' in content:
                        print("✅ .env 檔案包含 MongoDB 設定")
                    else:
                        print("⚠️  .env 檔案不包含 MongoDB 設定")
            except Exception as e:
                print(f"⚠️  讀取 .env 檔案失敗: {e}")
        else:
            print(f"\n📁 未發現 .env 檔案")
            print("💡 建議創建 .env 檔案來設定環境變數")
            
        return env_vars

    def show_connection_help(self):
        """顯示連接幫助資訊"""
        print("\n🔗 MongoDB 連接幫助")
        print("=" * 50)
        
        if os.path.exists('/.dockerenv'):
            print("🐳 檢測到 Docker 環境")
            print("   使用容器名稱連接: mongo:27017")
        else:
            print("🖥️  檢測到主機環境")
            print("   使用 localhost 連接: localhost:27017")
            
        print("\n📋 常用連接字串:")
        print("   Docker 容器內: mongodb://admin:changeme@mongo:27017/?authSource=admin")
        print("   主機環境: mongodb://admin:changeme@localhost:27017/?authSource=admin")
        print("   無認證: mongodb://localhost:27017/")
        
        print("\n🔧 設定環境變數:")
        print("   export MONGO_URI='mongodb://admin:changeme@localhost:27017/?authSource=admin'")
        print("   export MONGO_DB_NAME='interview_db'")
        
        print("\n🐳 Docker 命令:")
        print("   啟動服務: docker-compose up -d")
        print("   檢查狀態: docker-compose ps")
        print("   查看日誌: docker-compose logs mongo")
        print("   重啟服務: docker-compose restart mongo")

    def check_docker_environment(self) -> Dict[str, Any]:
        """檢查 Docker 環境狀態"""
        import subprocess
        import json
        
        status = {
            'docker_available': False,
            'containers_running': False,
            'mongo_container': False,
            'mongo_port': False,
            'connection_test': False
        }
        
        try:
            # 檢查 Docker 是否可用
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status['docker_available'] = True
                logger.info("🐳 Docker 可用")
            else:
                logger.warning("⚠️  Docker 不可用")
                return status
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("⚠️  Docker 命令未找到或超時")
            return status
            
        try:
            # 檢查容器狀態
            result = subprocess.run(['docker-compose', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                containers = result.stdout.strip().split('\n')
                for container in containers:
                    if container:
                        try:
                            container_info = json.loads(container)
                            if container_info.get('Service') == 'mongo':
                                status['mongo_container'] = container_info.get('State') == 'Up'
                                logger.info(f"📦 MongoDB 容器狀態: {container_info.get('State')}")
                        except json.JSONDecodeError:
                            continue
                            
                status['containers_running'] = True
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("⚠️  Docker Compose 命令未找到或超時")
            
        # 檢查 MongoDB 端口
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 27017))
            sock.close()
            status['mongo_port'] = result == 0
            if status['mongo_port']:
                logger.info("🔌 MongoDB 端口 27017 可訪問")
            else:
                logger.warning("⚠️  MongoDB 端口 27017 不可訪問")
        except Exception as e:
            logger.warning(f"⚠️  端口檢查失敗: {e}")
            
        return status

    def test_connection_with_fallback(self) -> bool:
        """測試連接，如果失敗則嘗試其他連接方式"""
        # 首先嘗試當前設定
        if self.connect_to_mongodb():
            return True
            
        # 如果失敗，嘗試其他連接方式
        fallback_uris = [
            "mongodb://admin:changeme@localhost:27017/?authSource=admin",
            "mongodb://admin:changeme@127.0.0.1:27017/?authSource=admin",
            "mongodb://admin:changeme@mongo:27017/?authSource=admin",
            "mongodb://localhost:27017/",  # 無認證
            "mongodb://127.0.0.1:27017/"  # 無認證
        ]
        
        logger.info("🔄 嘗試備用連接方式...")
        
        for i, uri in enumerate(fallback_uris):
            if uri == self.mongo_uri:
                continue  # 跳過已嘗試過的
                
            logger.info(f"🔄 嘗試備用連接 {i+1}: {uri.split('@')[1] if '@' in uri else uri}")
            self.mongo_uri = uri
            
            if self.connect_to_mongodb():
                logger.info(f"✅ 備用連接成功: {uri.split('@')[1] if '@' in uri else uri}")
                return True
                
        logger.error("❌ 所有連接方式都失敗")
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
    print("3. 檢查 Docker 環境")
    print("4. 測試 MongoDB 連接")
    print("5. 顯示環境變數設定")
    print("6. 顯示連接幫助")
    print("7. 退出")

    while True:
        choice = input("\n請輸入選項 (1-7): ").strip()

        if choice == "1":
            print("\n開始匯入 CSV 檔案...")
            
            # 先檢查連接
            if not importer.test_connection_with_fallback():
                print("❌ 無法連接到 MongoDB，請先檢查連接")
                continue
                
            results = importer.import_all_csv_files()

            if results:
                print("\n✅ 匯入完成！")
            else:
                print("\n❌ 匯入失敗！")

        elif choice == "2":
            if not importer.test_connection_with_fallback():
                print("❌ 無法連接到 MongoDB，請先檢查連接")
                continue
            importer.list_collections()

        elif choice == "3":
            print("\n🔍 檢查 Docker 環境...")
            status = importer.check_docker_environment()
            
            print("\n📊 Docker 環境狀態:")
            print(f"   🐳 Docker 可用: {'✅' if status['docker_available'] else '❌'}")
            print(f"   📦 容器運行中: {'✅' if status['containers_running'] else '❌'}")
            print(f"   🍃 MongoDB 容器: {'✅' if status['mongo_container'] else '❌'}")
            print(f"   🔌 MongoDB 端口: {'✅' if status['mongo_port'] else '❌'}")
            
            if not status['docker_available']:
                print("\n💡 建議:")
                print("   1. 安裝 Docker: sudo apt install docker.io")
                print("   2. 啟動 Docker 服務: sudo systemctl start docker")
                print("   3. 將用戶加入 docker 群組: sudo usermod -aG docker $USER")
                
            elif not status['mongo_container']:
                print("\n💡 建議:")
                print("   1. 啟動 MongoDB 容器: docker-compose up -d mongo")
                print("   2. 檢查容器狀態: docker-compose ps")
                print("   3. 查看容器日誌: docker-compose logs mongo")

        elif choice == "4":
            print("\n🔗 測試 MongoDB 連接...")
            if importer.test_connection_with_fallback():
                print("✅ MongoDB 連接成功！")
            else:
                print("❌ MongoDB 連接失敗！")
                print("\n💡 故障排除建議:")
                print("   1. 確保 MongoDB 服務正在運行")
                print("   2. 檢查防火牆設定")
                print("   3. 如果使用 Docker，確保容器正在運行")
                print("   4. 檢查連接字串是否正確")

        elif choice == "5":
            importer.setup_environment_variables()

        elif choice == "6":
            importer.show_connection_help()

        elif choice == "7":
            print("👋 再見！")
            break

        else:
            print("❌ 無效選項，請重新輸入")


if __name__ == "__main__":
    main()
