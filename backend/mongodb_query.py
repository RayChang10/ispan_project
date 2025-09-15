#!/usr/bin/env python3
"""
MongoDB 查詢工具 - Python 版本
模擬 MongoDB Shell 的功能
"""

import json
from typing import Any, Dict, List

from pymongo import MongoClient


class MongoDBQueryTool:
    """MongoDB 查詢工具"""

    def __init__(self):
        """初始化查詢工具"""
        self.client = MongoClient()
        self.db = self.client.interview_db
        self.current_collection = None

    def show_databases(self):
        """顯示所有資料庫"""
        databases = self.client.list_database_names()
        print("=== 可用資料庫 ===")
        for db_name in databases:
            print(f"  {db_name}")

    def use_database(self, db_name: str):
        """切換資料庫"""
        if db_name in self.client.list_database_names():
            self.db = self.client[db_name]
            print(f"✅ 已切換到資料庫: {db_name}")
        else:
            print(f"❌ 資料庫 {db_name} 不存在")

    def show_collections(self):
        """顯示所有集合"""
        collections = self.db.list_collection_names()
        print(f"=== 資料庫 {self.db.name} 中的集合 ===")
        for i, collection_name in enumerate(collections, 1):
            count = self.db[collection_name].count_documents({})
            print(f"  {i}. {collection_name} ({count} 筆資料)")

    def use_collection(self, collection_name: str):
        """選擇集合"""
        if collection_name in self.db.list_collection_names():
            self.current_collection = self.db[collection_name]
            print(f"✅ 已選擇集合: {collection_name}")
        else:
            print(f"❌ 集合 {collection_name} 不存在")

    def find_documents(self, limit: int = 5, pretty: bool = True):
        """查詢文件"""
        if self.current_collection is None:
            print("❌ 請先選擇集合 (use collection_name)")
            return

        documents = list(self.current_collection.find().limit(limit))
        print(
            f"=== 集合 {self.current_collection.name} 的前 {len(documents)} 筆資料 ==="
        )

        for i, doc in enumerate(documents, 1):
            print(f"\n--- 文件 {i} ---")
            if pretty:
                self._print_document_pretty(doc)
            else:
                print(json.dumps(doc, ensure_ascii=False, indent=2))

    def find_by_query(self, query_str: str, limit: int = 5):
        """根據查詢條件查找文件"""
        if not self.current_collection:
            print("❌ 請先選擇集合 (use collection_name)")
            return

        try:
            # 簡單的查詢解析
            query = self._parse_query(query_str)
            documents = list(self.current_collection.find(query).limit(limit))

            print(f"=== 查詢結果: {len(documents)} 筆資料 ===")
            for i, doc in enumerate(documents, 1):
                print(f"\n--- 文件 {i} ---")
                self._print_document_pretty(doc)

        except Exception as e:
            print(f"❌ 查詢錯誤: {e}")

    def count_documents(self, query_str: str = "{}"):
        """計算文件數量"""
        if not self.current_collection:
            print("❌ 請先選擇集合 (use collection_name)")
            return

        try:
            query = self._parse_query(query_str)
            count = self.current_collection.count_documents(query)
            print(f"集合 {self.current_collection.name} 中符合條件的文件數量: {count}")
        except Exception as e:
            print(f"❌ 計算錯誤: {e}")

    def search_text(self, text: str, limit: int = 5):
        """文字搜尋"""
        if not self.current_collection:
            print("❌ 請先選擇集合 (use collection_name)")
            return

        try:
            # 使用文字索引搜尋
            documents = list(
                self.current_collection.find({"$text": {"$search": text}}).limit(limit)
            )

            print(f"=== 文字搜尋 '{text}' 結果: {len(documents)} 筆資料 ===")
            for i, doc in enumerate(documents, 1):
                print(f"\n--- 文件 {i} ---")
                self._print_document_pretty(doc)

        except Exception as e:
            print(f"❌ 文字搜尋錯誤: {e}")

    def _parse_query(self, query_str: str) -> Dict[str, Any]:
        """解析查詢字串"""
        try:
            return json.loads(query_str)
        except json.JSONDecodeError:
            # 簡單的查詢解析
            if ":" in query_str:
                key, value = query_str.split(":", 1)
                return {key.strip(): value.strip()}
            else:
                return {}

    def _print_document_pretty(self, doc: Dict[str, Any]):
        """美化輸出文件"""
        for key, value in doc.items():
            if key == "_id":
                continue
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")

    def show_help(self):
        """顯示幫助"""
        print(
            """
=== MongoDB 查詢工具幫助 ===
命令列表:
  show dbs                    - 顯示所有資料庫
  use <database>              - 切換資料庫
  show collections            - 顯示所有集合
  use <collection>            - 選擇集合
  find [limit]                - 查詢文件 (預設5筆)
  find <query> [limit]        - 根據條件查詢
  count [query]               - 計算文件數量
  search <text> [limit]       - 文字搜尋
  help                        - 顯示此幫助
  exit                        - 退出程式

查詢範例:
  find 10                     - 查詢前10筆資料
  find {"題目": "algorithm"}   - 查詢包含 algorithm 的題目
  count                       - 計算總文件數
  search "blockchain"         - 搜尋包含 blockchain 的文件

範例操作:
  1. show collections         - 查看所有集合
  2. use algorithm1           - 選擇 algorithm1 集合
  3. find 3                   - 查看前3筆資料
        """
        )

    def run(self):
        """運行查詢工具"""
        print("🚀 MongoDB 查詢工具 (Python 版本)")
        print("輸入 'help' 查看幫助，輸入 'exit' 退出")
        print("=" * 50)

        while True:
            try:
                command = input(f"\n[{self.db.name}]> ").strip()

                if not command:
                    continue

                parts = command.split()
                cmd = parts[0].lower()

                if cmd == "exit":
                    print("👋 再見！")
                    break
                elif cmd == "help":
                    self.show_help()
                elif cmd == "show" and len(parts) > 1:
                    if parts[1] == "dbs":
                        self.show_databases()
                    elif parts[1] == "collections":
                        self.show_collections()
                elif cmd == "use" and len(parts) > 1:
                    if (
                        self.current_collection
                        and parts[1] in self.db.list_collection_names()
                    ):
                        self.use_collection(parts[1])
                    else:
                        self.use_database(parts[1])
                elif cmd == "find":
                    if len(parts) == 1:
                        self.find_documents()
                    elif len(parts) == 2 and parts[1].isdigit():
                        self.find_documents(int(parts[1]))
                    else:
                        query = " ".join(parts[1:])
                        limit = 5
                        if parts[-1].isdigit():
                            limit = int(parts[-1])
                            query = " ".join(parts[1:-1])
                        self.find_by_query(query, limit)
                elif cmd == "count":
                    query = " ".join(parts[1:]) if len(parts) > 1 else "{}"
                    self.count_documents(query)
                elif cmd == "search" and len(parts) > 1:
                    text = parts[1]
                    limit = (
                        int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 5
                    )
                    self.search_text(text, limit)
                else:
                    print("❌ 未知命令，輸入 'help' 查看幫助")

            except KeyboardInterrupt:
                print("\n👋 再見！")
                break
            except Exception as e:
                print(f"❌ 錯誤: {e}")


def main():
    """主程式"""
    tool = MongoDBQueryTool()
    tool.run()


if __name__ == "__main__":
    main()
