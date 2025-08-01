# MCP 智能面試工具套件

## 📋 項目概述

這是一個基於 MCP (Model Context Protocol) 的智能面試系統，提供模組化的面試工具套件。系統支援多種面試模式，包括技術面試、行為面試和綜合評估。

### ✨ 主要功能

- 🤖 **智能問題生成**: 基於 MongoDB 資料庫的隨機問題抽取
- 📊 **答案分析**: AI 驅動的答案評估和反饋
- 🎯 **面試流程管理**: 完整的面試會話追蹤
- 🎨 **用戶介面**: 直觀的互動式介面
- 📈 **表現評估**: 詳細的表現分析和建議

## 📁 項目結構

```
tools/
├── __init__.py              # 模組初始化檔案
├── database.py              # 資料庫連接與管理
├── question_manager.py      # 問題管理與抽取
├── answer_analyzer.py       # 答案分析與評估
├── interview_session.py     # 面試流程管理
├── ui_manager.py           # 用戶介面管理
├── interactive_interview.py # 主整合模組
└── README.md               # 說明檔案
```

## 🚀 快速開始

### 安裝依賴

```bash
pip install -r requirements.txt
```

### 基本使用

```python
from tools import InteractiveInterview

# 創建面試實例
interviewer = InteractiveInterview()

# 開始互動式面試
await interviewer.run_interactive_session()
```

## 🔧 模組詳解

### 1. `database.py` - 資料庫管理模組

**功能**: 負責 MongoDB 連接和基本操作

**主要類別**: `DatabaseManager`

**核心方法**:
- `connect()`: 建立 MongoDB 連接
- `get_collections()`: 獲取所有集合名稱
- `get_random_document()`: 從指定集合獲取隨機文檔
- `get_document_by_id()`: 根據 ID 獲取文檔

**使用範例**:
```python
from tools import db_manager

# 連接資料庫
db_manager.connect()

# 獲取隨機問題
question_doc = db_manager.get_random_document("python_questions")
```

### 2. `question_manager.py` - 問題管理模組

**功能**: 負責面試問題的獲取和管理

**主要類別**: `QuestionManager`

**核心方法**:
- `get_random_question()`: 獲取隨機面試問題
- `get_question_by_category()`: 根據類別獲取問題
- `_extract_question()`: 從文檔中提取問題內容
- `_extract_answer()`: 從文檔中提取標準答案

**使用範例**:
```python
from tools import question_manager

# 獲取隨機問題
question_data = question_manager.get_random_question()
print(f"問題: {question_data['question']}")
print(f"標準答案: {question_data['answer']}")
```

### 3. `answer_analyzer.py` - 答案分析模組

**功能**: 分析用戶回答與標準答案的差異

**主要類別**: `AnswerAnalyzer`

**核心方法**:
- `analyze_answer()`: 分析用戶回答
- `get_detailed_analysis()`: 獲取詳細分析結果
- `_analyze_differences()`: 分析回答差異
- `_evaluate_performance()`: 評估表現等級

**使用範例**:
```python
from tools import answer_analyzer

# 分析答案
analysis = answer_analyzer.analyze_answer(
    user_answer="我的回答內容",
    standard_answer="標準答案內容"
)

print(f"相似度: {analysis['similarity']}")
print(f"評分: {analysis['score']}")
```

### 4. `interview_session.py` - 面試流程模組

**功能**: 管理整個面試流程和會話狀態

**主要類別**: `InterviewSession`

**核心方法**:
- `start_session()`: 開始新的面試會話
- `get_next_question()`: 獲取下一個問題
- `submit_answer()`: 提交用戶回答
- `get_session_summary()`: 獲取會話摘要
- `end_session()`: 結束面試會話

**使用範例**:
```python
from tools import interview_session

# 開始面試會話
session = interview_session.start_session()

# 獲取問題
question = interview_session.get_next_question()

# 提交答案
interview_session.submit_answer("用戶回答", "標準答案")

# 獲取摘要
summary = interview_session.get_session_summary()
```

### 5. `ui_manager.py` - 用戶介面模組

**功能**: 處理用戶互動和顯示

**主要類別**: `UIManager`

**核心方法**:
- `display_welcome()`: 顯示歡迎訊息
- `display_question()`: 顯示面試問題
- `display_analysis()`: 顯示分析結果
- `get_user_input()`: 獲取用戶輸入
- `display_progress()`: 顯示進度

**使用範例**:
```python
from tools import ui_manager

# 顯示歡迎訊息
ui_manager.display_welcome()

# 顯示問題
ui_manager.display_question("請解釋什麼是 Python 的裝飾器？")

# 獲取用戶輸入
user_input = ui_manager.get_user_input("請輸入您的答案: ")
```

### 6. `interactive_interview.py` - 主整合模組

**功能**: 整合所有模組，提供完整的互動式面試功能

**主要類別**: `InteractiveInterview`

**核心方法**:
- `conduct_interview()`: 進行互動式面試
- `run_interactive_session()`: 運行互動式會話
- `get_random_question()`: 獲取隨機問題
- `analyze_answer()`: 分析答案

**使用範例**:
```python
from tools import InteractiveInterview

# 創建面試實例
interviewer = InteractiveInterview()

# 運行完整面試
await interviewer.run_interactive_session()
```

## 🎯 進階使用

### 模組化使用

```python
from tools import (
    question_manager, 
    answer_analyzer, 
    interview_session,
    ui_manager
)

# 自定義面試流程
session = interview_session.start_session()

for i in range(5):  # 進行 5 個問題的面試
    # 獲取問題
    question_data = question_manager.get_random_question()
    
    # 顯示問題
    ui_manager.display_question(question_data['question'])
    
    # 獲取用戶回答
    user_answer = ui_manager.get_user_input("您的答案: ")
    
    # 分析答案
    analysis = answer_analyzer.analyze_answer(
        user_answer, 
        question_data['answer']
    )
    
    # 顯示分析結果
    ui_manager.display_analysis(analysis)
    
    # 提交到會話
    interview_session.submit_answer(user_answer, question_data['answer'])

# 顯示最終結果
summary = interview_session.get_session_summary()
ui_manager.display_summary(summary)
```

### 自定義配置

```python
from tools import db_manager, question_manager

# 配置資料庫連接
db_manager.configure(
    host="localhost",
    port=27017,
    database="interview_db"
)

# 配置問題管理器
question_manager.configure(
    default_collection="python_questions",
    max_questions=10
)
```

## 🧪 測試

### 運行測試

```bash
# 運行所有測試
python -m pytest tests/

# 運行特定模組測試
python -m pytest tests/test_database.py

# 運行並顯示詳細輸出
python -m pytest -v
```

### 單元測試範例

```python
import pytest
from tools import question_manager, answer_analyzer

def test_question_manager():
    """測試問題管理器"""
    question = question_manager.get_random_question()
    assert 'question' in question
    assert 'answer' in question

def test_answer_analyzer():
    """測試答案分析器"""
    analysis = answer_analyzer.analyze_answer(
        "Python 是一種程式語言",
        "Python 是一種高級程式語言"
    )
    assert 'similarity' in analysis
    assert 'score' in analysis
```

## 📊 API 參考

### DatabaseManager

| 方法 | 參數 | 返回值 | 描述 |
|------|------|--------|------|
| `connect()` | `host`, `port`, `database` | `bool` | 連接 MongoDB |
| `get_collections()` | - | `list` | 獲取所有集合 |
| `get_random_document()` | `collection_name` | `dict` | 獲取隨機文檔 |

### QuestionManager

| 方法 | 參數 | 返回值 | 描述 |
|------|------|--------|------|
| `get_random_question()` | - | `dict` | 獲取隨機問題 |
| `get_question_by_category()` | `category` | `dict` | 根據類別獲取問題 |

### AnswerAnalyzer

| 方法 | 參數 | 返回值 | 描述 |
|------|------|--------|------|
| `analyze_answer()` | `user_answer`, `standard_answer` | `dict` | 分析答案 |
| `get_detailed_analysis()` | `user_answer`, `standard_answer` | `dict` | 獲取詳細分析 |

## 🔄 版本歷史

### v2.1.0 (當前版本)
- ✅ 新增模組化架構
- ✅ 改善錯誤處理
- ✅ 優化性能
- ✅ 新增詳細文檔

### v2.0.0
- ✅ 重構為模組化架構
- ✅ 新增資料庫管理模組
- ✅ 新增答案分析模組

### v1.0.0
- ✅ 初始版本
- ✅ 基本面試功能

## 🤝 貢獻指南

1. Fork 本項目
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📄 授權

本項目採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 文件

## 📞 支援

如有問題或建議，請：

1. 查看 [Issues](../../issues) 頁面
2. 創建新的 Issue
3. 聯繫開發團隊

---

**版本**: 2.1.0  
**作者**: MCP Team  
**最後更新**: 2024年12月 