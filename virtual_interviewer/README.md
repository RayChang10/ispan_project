# 虛擬面試顧問 (Virtual Interview Consultant)

一個整合職缺媒合、履歷健檢、虛擬面試功能的AI輔助平台，專為求職者設計的完整解決方案。

## 🎯 專案特色

- **虛擬面試**: AI驅動的模擬面試體驗
- **履歷建立**: 完整的履歷資料管理系統
- **即時互動**: 支援語音輸入與檔案上傳
- **響應式設計**: 支援桌面與行動裝置
- **RESTful API**: 模組化後端架構

## 🏗️ 技術架構

### 後端
- **Flask**: Web框架
- **SQLAlchemy**: ORM資料庫管理
- **Flask-RESTful**: RESTful API開發
- **SQLite**: 輕量級資料庫

### 前端
- **Bootstrap 5**: UI框架
- **jQuery**: JavaScript函式庫
- **Font Awesome**: 圖標系統
- **Web Speech API**: 語音識別

## 📦 安裝說明

### 環境需求
- Python 3.8.1+
- Poetry (推薦) 或 pip

### 🎯 快速開始 (使用Poetry - 推薦)

#### 1. 安裝Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

#### 2. 克隆專案
```bash
git clone <repository-url>
cd virtual_interviewer
```

#### 3. 安裝依賴並啟動
```bash
# 使用便利腳本
./start.sh

# 或手動執行
poetry install
poetry run python run.py
```

### 💻 開發環境設置
```bash
# 設置開發環境（包含測試和程式碼檢查工具）
./dev.sh

# 手動設置
poetry install --with dev
poetry shell  # 進入虛擬環境
```

### 🔧 傳統方式 (使用pip)
```bash
# 如果不使用Poetry，可以使用pip安裝
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

pip install flask flask-cors flask-sqlalchemy flask-restful python-dotenv marshmallow
python run.py
```

## 🚀 啟動應用

### 🎯 使用Poetry (推薦)
```bash
# 快速啟動
./start.sh

# 手動啟動
poetry run python run.py

# 開發模式（包含程式碼檢查工具）
./dev.sh
```

### 🔧 其他啟動方式
```bash
# 直接使用Poetry shell
poetry shell
python run.py

# 生產環境 (使用Gunicorn)
poetry run gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 傳統方式
python run.py
```

應用程式將在 `http://localhost:5000` 啟動

## 📱 功能說明

### 主頁面功能
- **虛擬面試官**: 左側顯示AI面試官頭像
- **對話介面**: 支援文字和語音輸入
- **檔案上傳**: 支援PDF、Word格式履歷
- **即時對話**: AI智能回應系統

### 履歷建立功能
- **基本資料**: 姓名、期望職稱、工作領域等
- **專業技能**: 動態新增技能名稱與描述
- **工作經驗**: 動態新增多個工作經歷
- **技能關鍵字**: 可新增多個專業技能
- **草稿儲存**: 自動和手動儲存功能

## 📁 專案結構

```
virtual_interviewer/
├── pyproject.toml         # Poetry專案配置
├── app.py                 # Flask主應用程式
├── run.py                 # 應用程式啟動腳本
├── start.sh              # Poetry快速啟動腳本
├── dev.sh                # 開發環境設置腳本
├── README.md             # 專案說明文件
├── UPDATE_LOG.md         # 更新記錄
├── templates/            # HTML模板
│   ├── base.html         # 基礎模板
│   ├── index.html        # 主頁面
│   └── resume.html       # 履歷建立頁面
├── static/               # 靜態資源
│   ├── css/
│   │   └── style.css     # 自定義樣式
│   ├── js/
│   │   ├── app.js        # 通用JavaScript
│   │   ├── interview.js  # 面試頁面功能
│   │   └── resume.js     # 履歷頁面功能
│   └── img/              # 圖片資源
└── instance/             # SQLite資料庫目錄
    └── virtual_interview.db  # SQLite資料庫(自動生成)
```

## 🔧 API端點

### 用戶管理
- `POST /api/users` - 創建用戶履歷
- `GET /api/users` - 取得所有用戶
- `GET /api/users/<id>` - 取得特定用戶資料

### 面試功能
- `POST /api/interview` - 處理面試對話

### 檔案上傳
- `POST /api/upload` - 處理履歷檔案上傳

### 🤖 Fay數字人整合API (v1.3.0)
- `POST /api/avatar/control` - 虛擬人狀態控制（說話、聆聽、表情、待機）
- `POST /api/tts/generate` - 文字轉語音生成
- `POST /api/avatar/lipsync` - 唇形同步資料生成
- `POST /api/fay/integration` - Fay系統專用整合接口

### 🎤 語音識別API (STT) (v1.4.0)
- `POST /api/stt` - 語音轉文字（支援Whisper、Azure、Google等多種引擎）
- `POST /api/speech` - 語音處理綜合API（整合STT和TTS功能）

## 🛠️ 開發者串接指引

### 🎯 快速開始串接
如果您要開發其他功能或整合第三方服務，請參考以下指引：

#### 1. **API 串接範例**
```javascript
// 基本 API 調用範例
const response = await fetch('/api/interview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: '您好！' })
});
const data = await response.json();
```

#### 2. **Fay數字人整合**
```javascript
// 引入虛擬人管理器
import { FayAvatarManager } from '/static/js/avatar.js';

// 讓虛擬人說話
await FayAvatarManager.speak("歡迎來到面試！", {
    emotion: 'happy',
    voice: 'zh-TW-female'
});

// 設定表情
await FayAvatarManager.setEmotion('happy', 0.8);
```

#### 3. **WebSocket 通訊**
```javascript
// 建立 Fay WebSocket 連接
const ws = new WebSocket('ws://localhost:8080/fay');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Fay回應:', data);
};
```

#### 4. **語音識別 (STT)**
```javascript
// Whisper語音識別範例
const formData = new FormData();
formData.append('audio', audioFile);
formData.append('engine', 'whisper');
formData.append('language', 'zh-TW');
formData.append('model_size', 'base');

const response = await fetch('/api/stt', {
    method: 'POST',
    body: formData
});
const result = await response.json();
console.log('識別結果:', result.transcription);
```

#### 5. **完整語音互動流程**
```javascript
// 錄音 → STT → AI處理 → TTS → 虛擬人播放
async function voiceInteraction() {
    // 1. 錄音（使用Web Audio API）
    const audioBlob = await recordAudio();
    
    // 2. 語音轉文字
    const sttResult = await transcribeAudio(audioBlob);
    
    // 3. 發送到AI進行處理
    const aiResponse = await fetch('/api/interview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: sttResult.transcription })
    });
    
    // 4. AI回應轉語音並播放
    const aiData = await aiResponse.json();
    await FayAvatarManager.speak(aiData.response, {
        emotion: 'friendly'
    });
}
```

### 📚 詳細文檔參考
- **[FAY_INTEGRATION_API.md](./FAY_INTEGRATION_API.md)** - 完整的Fay數字人整合API文檔
  - 詳細的API請求/回應格式
  - JavaScript整合範例
  - WebSocket通訊協議
  - TTS引擎整合選項
  - 部署配置指引

- **[UPDATE_LOG.md](./UPDATE_LOG.md)** - 功能更新記錄
  - 各版本新增功能詳細說明
  - API變更歷史
  - 技術架構演進

### 🔌 第三方整合支援

#### TTS (文字轉語音) 整合
- **Azure Cognitive Services Speech** - 高品質中文語音
- **Google Cloud Text-to-Speech** - WaveNet神經網路語音
- **Amazon Polly** - 神經語音合成
- **本地TTS引擎** - espeak, festival

#### STT (語音轉文字) 整合
- **OpenAI Whisper** - 高精度多語言語音識別（推薦）
  - 支援多種模型大小：tiny, base, small, medium, large
  - 優秀的中文識別能力
  - 本地部署，保護隱私
- **Azure Cognitive Services Speech** - 雲端語音識別服務
- **Google Cloud Speech-to-Text** - 強大的雲端STT
- **自定義STT引擎** - 支援其他STT服務整合

#### 數字人系統整合
- **Fay數字人** - 完整的語音表情對嘴支援
- **擴展接口** - 支援其他數字人模型整合

### 🌐 環境配置
```bash
# TTS服務配置
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=eastasia

# Fay系統配置
FAY_WEBSOCKET_URL=ws://localhost:8080/fay
FAY_API_KEY=your_fay_api_key

# STT語音識別配置
WHISPER_MODEL_SIZE=base  # tiny, base, small, medium, large
WHISPER_LANGUAGE=zh-TW
AZURE_STT_KEY=your_azure_stt_key
GOOGLE_STT_CREDENTIALS=path/to/google-credentials.json

# 音頻處理配置
MAX_AUDIO_FILE_SIZE=25MB
SUPPORTED_AUDIO_FORMATS=wav,mp3,m4a,flac
```

### 🔧 常用開發模式

#### 1. **API擴展開發**
```python
# 在 app.py 中添加新的API資源
class CustomAPI(Resource):
    def post(self):
        # 自定義邏輯
        return {'success': True, 'data': result}

# 註冊API路由
api.add_resource(CustomAPI, '/api/custom')
```

#### 2. **前端功能擴展**
```javascript
// 擴展現有功能
const MyCustomManager = {
    init: function() {
        // 初始化邏輯
    },
    
    processData: function(data) {
        // 資料處理邏輯
    }
};
```

#### 3. **資料庫模型擴展**
```python
# 新增資料表模型
class CustomModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # 其他欄位...
```

### 🧪 測試與偵錯
```bash
# 程式碼格式化
poetry run black .

# 程式碼檢查
poetry run flake8 .

# 執行測試
poetry run pytest

# 查看API回應
curl -X POST http://localhost:5000/api/avatar/control \
  -H "Content-Type: application/json" \
  -d '{"action": "speak", "text": "測試語音"}'

# 測試STT語音識別
curl -X POST http://localhost:5000/api/stt \
  -F "audio=@test_audio.wav" \
  -F "engine=whisper" \
  -F "language=zh-TW"

# 測試語音處理綜合API
curl -X POST http://localhost:5000/api/speech \
  -H "Content-Type: application/json" \
  -d '{"action": "transcribe"}'
```

## 🎨 介面預覽

### 主頁面
- 左側：虛擬AI面試官
- 右側：對話區域與輸入控制

### 履歷頁面
- 分段式表單設計
- 動態欄位新增功能
- 即時驗證與草稿儲存

## 🔮 未來功能規劃

### Phase 1 (MVP) - ✅ 已完成
- [x] 基本前後端架構
- [x] 履歷建立系統
- [x] 專業技能管理功能
- [x] 簡單AI對話模擬
- [x] 檔案上傳功能

### Phase 2 - 🚧 開發中
- [ ] 整合真實AI模型 (OpenAI/Anthropic)
- [ ] 履歷檔案自動解析
- [ ] 面試問題智能生成
- [ ] 語音合成回應

### Phase 3 - 📋 規劃中
- [ ] 職缺媒合功能
- [ ] 面試表現分析
- [ ] 個人化建議系統
- [ ] 多語言支援

## 🛠️ 開發指引

### 程式碼風格
- 遵循PEP 8 Python風格指南
- 使用有意義的變數和函數命名
- 適當的註解和文檔字串

### 資料庫設計
- 使用SQLAlchemy ORM
- 適當的外鍵關聯
- 資料驗證和約束

### 前端開發
- 響應式設計優先
- 漸進式功能增強
- 無障礙設計考量

## 🤝 貢獻指南

1. Fork 專案
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📄 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 👥 開發團隊

- **專案架構**: 全端開發
- **UI/UX設計**: Bootstrap主題客製化
- **AI整合**: 預留OpenAI/Anthropic API接口

## 📞 聯絡資訊

如有任何問題或建議，請透過以下方式聯絡：
- Email: [contact@virtual-interview.com]
- GitHub Issues: [專案Issues頁面]

---

⭐ 如果這個專案對您有幫助，請給我們一個星星！ 