# Fay數字人整合API文檔

## 🎯 概述

虛擬面試顧問已完整預留並實現了與 **Fay數字人模型** 整合的API接口，支援語音表情對嘴、TTS語音合成、唇形同步等完整功能。

## 🤖 虛擬人API架構

### **1. 虛擬人狀態控制API**
```
POST /api/avatar/control
```

#### 功能說明
控制虛擬人的各種狀態和動作，包括說話、聆聽、表情、待機等。

#### 請求格式
```json
{
    "action": "speak|listen|emotion|idle",
    "text": "要說的文字",
    "voice_config": {
        "emotion": "neutral|happy|sad|surprised|angry",
        "voice": "zh-TW-female",
        "speed": 1.0
    },
    "emotion": "happy",
    "intensity": 0.8
}
```

#### 回應格式
```json
{
    "success": true,
    "audio_url": "/api/avatar/audio/latest",
    "lip_sync_data": [...],
    "duration": 3.5,
    "emotion": "neutral",
    "state": "speaking|listening|idle",
    "animation": "speaking_idle",
    "transition_duration": 1.0
}
```

### **2. 文字轉語音API (TTS)**
```
POST /api/tts/generate
```

#### 功能說明
將文字轉換為語音檔案，支援多種TTS引擎和語音配置。

#### 請求格式
```json
{
    "text": "您好！我是您的虛擬面試顧問",
    "voice": "zh-TW-female",
    "speed": 1.0,
    "emotion": "neutral"
}
```

#### 回應格式
```json
{
    "success": true,
    "audio_url": "/api/tts/audio/uuid-123",
    "duration": 3.2,
    "phonemes": [...],
    "voice_config": {
        "voice": "zh-TW-female",
        "speed": 1.0,
        "emotion": "neutral"
    }
}
```

### **3. 唇形同步API**
```
POST /api/avatar/lipsync
```

#### 功能說明
根據音頻檔案和文字生成唇形同步資料，與Fay系統兼容。

#### 請求格式
```json
{
    "audio_file": "audio_file_path",
    "text": "對應的文字內容"
}
```

#### 回應格式
```json
{
    "success": true,
    "lip_sync_data": {...},
    "keyframes": [
        {"time": 0.0, "mouth_shape": "A"},
        {"time": 0.5, "mouth_shape": "O"},
        {"time": 1.0, "mouth_shape": "closed"}
    ],
    "format": "fay_compatible"
}
```

### **4. Fay專用整合API**
```
POST /api/fay/integration
```

#### 功能說明
專門為Fay數字人系統設計的整合接口，提供WebSocket連接和指令控制。

#### 請求格式
```json
{
    "command": "start_conversation|send_message|set_emotion|get_status",
    "message": "要發送的訊息",
    "emotion": "happy",
    "data": {...}
}
```

#### 回應格式
```json
{
    "success": true,
    "session_id": "fay_session_123",
    "status": "ready|active",
    "websocket_url": "ws://localhost:8080/fay",
    "message_sent": "訊息內容",
    "fay_response_pending": true,
    "emotion_set": "happy",
    "current_emotion": "neutral",
    "is_speaking": false,
    "conversation_active": true
}
```

### **5. 語音識別API (STT)**
```
POST /api/stt
```

#### 功能說明
將語音檔案轉換為文字，支援多種STT引擎，包含OpenAI Whisper（推薦）。

#### 請求格式（multipart/form-data）
```
audio: [音頻檔案] (必填)
engine: whisper|azure|google|custom (選填，預設whisper)
language: zh-TW|en-US|ja-JP|... (選填，預設zh-TW)
model_size: tiny|base|small|medium|large (選填，僅Whisper使用，預設base)
```

#### 支援的音頻格式
- WAV, MP3, M4A, FLAC
- 最大檔案大小：25MB
- 建議採樣率：16kHz或44.1kHz

#### 回應格式
```json
{
    "success": true,
    "transcription": "識別出的文字內容",
    "confidence": 0.96,
    "language": "zh-TW",
    "engine": "whisper",
    "processing_time": 1.2,
    "segments": [
        {
            "start": 0.0,
            "end": 2.5,
            "text": "識別出的文字內容"
        }
    ]
}
```

### **6. 語音處理綜合API**
```
POST /api/speech
```

#### 功能說明
整合語音轉文字(STT)和文字轉語音(TTS)的統一接口，支援即時語音處理。

#### 請求格式
```json
{
    "action": "transcribe|synthesize|realtime",
    "audio_data": "base64編碼的音頻資料",
    "text": "要合成的文字",
    "config": {
        "stt_engine": "whisper",
        "tts_voice": "zh-TW-female",
        "language": "zh-TW"
    }
}
```

#### 回應格式
```json
{
    "success": true,
    "action": "transcribe|synthesize|realtime",
    "result": {
        "transcription": "識別文字",
        "audio_url": "合成語音URL",
        "session_id": "語音會話ID"
    },
    "redirect_to": "/api/stt 或 /api/tts/generate",
    "websocket_url": "ws://localhost:5000/speech-realtime"
}
```

## 🔗 前端JavaScript整合

### **FayAvatarManager類別**

#### 主要方法
```javascript
// 初始化Fay系統
FayAvatarManager.init()

// 連接Fay數字人
await FayAvatarManager.connectToFay()

// 讓虛擬人說話
await FayAvatarManager.speak("您好！", {
    emotion: 'happy',
    voice: 'zh-TW-female'
})

// 設定表情
await FayAvatarManager.setEmotion('happy', 0.8)

// 設定聆聽狀態
await FayAvatarManager.setListening(true)

// 獲取當前狀態
const status = FayAvatarManager.getStatus()

// 語音識別 (STT)
await FayAvatarManager.transcribeAudio(audioBlob, {
    engine: 'whisper',
    language: 'zh-TW'
})

// 完整語音互動流程
await FayAvatarManager.voiceInteraction()
```

#### WebSocket事件處理
```javascript
// 語音開始事件
onSpeechStarted(data)

// 語音結束事件
onSpeechEnded(data)

// 表情變化事件
onEmotionChanged(data)

// 唇形同步資料事件
onLipSyncData(data)
```

## 🎭 支援的表情與動作

### **表情類型**
- `neutral` - 中性表情
- `happy` - 開心
- `sad` - 難過
- `surprised` - 驚訝
- `angry` - 生氣

### **動作狀態**
- `speaking` - 說話中
- `listening` - 聆聽中
- `idle` - 待機狀態
- `emotion` - 表情變化

### **語音配置**
- `zh-TW-female` - 中文女聲
- `zh-TW-male` - 中文男聲
- `en-US-female` - 英文女聲
- `en-US-male` - 英文男聲

## 🔌 Fay系統整合方案

### **WebSocket連接流程**
1. 調用 `/api/fay/integration` 建立會話
2. 獲取WebSocket URL
3. 建立WebSocket連接
4. 發送初始化指令
5. 開始雙向通訊

### **Fay指令格式**
```json
{
    "command": "speak|listen|set_emotion|initialize",
    "data": {
        "text": "要說的內容",
        "audio_url": "音頻檔案URL",
        "lip_sync_data": [...],
        "emotion": "happy",
        "intensity": 0.8,
        "avatar_type": "interview_consultant"
    },
    "timestamp": "2025-07-23T08:00:00.000Z"
}
```

### **Fay回傳格式**
```json
{
    "type": "speech_started|speech_ended|emotion_changed|lip_sync_data",
    "data": {
        "duration": 3.5,
        "emotion": "happy",
        "keyframes": [...]
    },
    "timestamp": "2025-07-23T08:00:00.000Z"
}
```

## 🛠️ TTS引擎整合選項

### **雲端TTS服務**
1. **Azure Cognitive Services Speech**
   - 高品質中文語音
   - 支援SSML語音標記
   - 豐富的語音效果

2. **Google Cloud Text-to-Speech**
   - WaveNet神經網路語音
   - 多種語言和口音
   - 自然語調

3. **Amazon Polly**
   - 神經語音合成
   - 情感語調控制
   - 批量處理

### **本地TTS解決方案**
1. **本地TTS引擎**
   - espeak, festival
   - 離線運作
   - 自定義語音模型

2. **Fay內建TTS**
   - 與數字人緊密整合
   - 優化的唇形同步
   - 低延遲響應

## 📱 前端控制面板

### **開發者控制介面**
在開發模式下（localhost），虛擬人左側會顯示控制面板：

- **連接Fay按鈕** - 建立與Fay的WebSocket連接
- **表情控制** - 😊😢😲 快速切換表情
- **測試語音** - 播放測試語音檢查功能

### **自動整合**
系統會自動在AI回應時觸發虛擬人說話：
```javascript
// 當AI發送訊息時自動觸發語音
InterviewManager.displayMessage = function(message, sender) {
    // 顯示訊息
    originalDisplayMessage.call(this, message, sender);
    
    // AI訊息觸發虛擬人說話
    if (sender === 'ai' && FayAvatarManager) {
        FayAvatarManager.speak(message, {
            emotion: 'neutral',
            voice: 'zh-TW-female'
        });
    }
};
```

## 🎨 視覺效果與動畫

### **說話狀態**
- 頭像邊框發光（綠色）
- 脈衝縮放動畫
- 狀態指示器顯示"AI正在說話"

### **聆聽狀態**
- 頭像邊框發光（藍色）
- 麥克風指示器
- 狀態指示器顯示"AI正在聆聽"

### **表情變化**
- 濾鏡效果模擬不同情緒
- 平滑過渡動畫
- 表情持續時間控制

## 🚀 使用範例

### **基本語音播放**
```javascript
// 簡單語音播放
await FayAvatarManager.speak("歡迎來到虛擬面試！");

// 帶表情的語音
await FayAvatarManager.speak("恭喜您通過面試！", {
    emotion: 'happy',
    voice: 'zh-TW-female',
    speed: 1.1
});
```

### **表情控制**
```javascript
// 設定開心表情
await FayAvatarManager.setEmotion('happy', 0.9);

// 延遲後恢復中性
setTimeout(() => {
    FayAvatarManager.setEmotion('neutral', 0.5);
}, 3000);
```

### **聆聽狀態切換**
```javascript
// 開始聆聽用戶輸入
await FayAvatarManager.setListening(true);

// 用戶說話結束後
await FayAvatarManager.setListening(false);
```

## 📈 性能優化建議

### **音頻檔案管理**
- 使用音頻壓縮 (MP3, AAC)
- 實現音頻檔案快取
- 預載常用語音片段

### **WebSocket最佳實踐**
- 心跳機制保持連接
- 斷線自動重連
- 訊息隊列處理

### **動畫效果優化**
- 使用CSS3硬體加速
- 合理的動畫幀率
- 減少DOM操作頻率

## 🔧 部署配置

### **環境變數設置**
```bash
# TTS服務配置
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=eastasia

# Fay系統配置
FAY_WEBSOCKET_URL=ws://localhost:8080/fay
FAY_API_KEY=your_fay_api_key

# 音頻檔案存儲
AUDIO_STORAGE_PATH=/static/audio/
MAX_AUDIO_FILE_SIZE=10MB
```

### **Docker配置**
```dockerfile
# 添加音頻處理依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak \
    festival

# 複製音頻資源
COPY static/audio/ /app/static/audio/
```

---

## ✨ 總結

虛擬面試顧問已完整實現了與Fay數字人系統的整合API，提供：

✅ **完整的API接口** - 虛擬人控制、TTS、唇形同步、Fay整合  
✅ **前端控制系統** - JavaScript管理器、WebSocket通訊、視覺效果  
✅ **表情與語音** - 多種表情、語音配置、動畫效果  
✅ **自動整合** - AI對話自動觸發虛擬人反應  
✅ **擴展性設計** - 支援多種TTS引擎、雲端服務整合  

現在您可以輕鬆接入Fay或其他數字人系統，實現完整的語音表情對嘴功能！🎭 