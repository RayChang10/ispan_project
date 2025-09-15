# 虛擬人同步功能指南

## 功能概述

本系統現在支援將面試頁面的虛擬人與 Dashboard (`http://localhost:8010/dashboard.html`) 的虛擬人進行同步，確保兩個頁面顯示相同的虛擬人狀態和對話內容。

## 功能特色

### 🔄 自動同步
- **Session 共享**：兩個頁面使用相同的 LiveTalking Session ID
- **狀態同步**：虛擬人的表情、動作、對話狀態保持一致
- **即時更新**：任一頁面的變化會自動反映到另一頁面

### 🎮 手動控制
- **同步開關**：可以隨時啟用或停用同步功能
- **立即同步**：手動觸發同步最新狀態
- **狀態顯示**：實時顯示同步狀態和 Session ID

### 🛡️ 錯誤處理
- **服務檢測**：自動檢測 LiveTalking 服務狀態
- **降級模式**：服務不可用時優雅降級
- **錯誤恢復**：自動重試和錯誤恢復機制

## 使用方法

### 1. 啟動服務
```bash
# 確保 LiveTalking 服務在 8010 端口運行
# 然後啟動面試系統
python -m backend.main --mode integrated
```

### 2. 訪問頁面
- **面試頁面**：http://localhost:8080
- **Dashboard 頁面**：http://localhost:8080/dashboard.html

### 3. 同步控制
在面試頁面的虛擬人區域，您會看到同步控制面板：

#### 同步開關
- ✅ **已勾選**：啟用同步模式
- ❌ **未勾選**：停用同步模式

#### 立即同步按鈕
- 點擊「立即同步」強制從 Dashboard 獲取最新 Session
- 按鈕會顯示同步進度

#### 狀態指示
- 🟢 **已同步 (xxxxxx)**：顯示當前 Session ID
- 🟡 **等待同步**：同步已啟用但尚未建立連接
- ⚪ **同步已停用**：同步功能關閉

## 技術實現

### Session 管理
```javascript
// localStorage 存儲共享 Session ID
localStorage.setItem('lt_shared_session_id', sessionId);

// 自動檢測 Session 變化
setInterval(() => {
    const currentId = localStorage.getItem('lt_shared_session_id');
    if (currentId !== previousId) {
        // 重新連接到新的 Session
        reconnectToSession(currentId);
    }
}, 5000);
```

### 代理配置
```python
# proxy.py 中的 Dashboard 代理
@app.route('/dashboard.html')
def dashboard():
    return requests.get('http://localhost:8010/dashboard.html')
```

### 同步流程
1. **啟動時**：檢查 localStorage 中的共享 Session ID
2. **獲取 Session**：從 `/ltapi/index.json` 獲取當前 Session
3. **保存同步**：將 Session ID 保存到 localStorage
4. **監控變化**：定期檢查 Session ID 變化
5. **自動重連**：檢測到變化時重新建立連接

## API 端點

### LiveTalking 代理
- `GET /ltapi/index.json` - 獲取當前 Session 信息
- `POST /ltapi/offer` - WebRTC 連接建立
- `POST /ltapi/human` - 發送語音指令

### Dashboard 代理
- `GET /dashboard.html` - 訪問 Dashboard 頁面
- 所有 Dashboard 資源透過代理訪問

## 配置選項

### JavaScript 配置
```javascript
window.LT_CONFIG = {
    speakPath: '/human',
    speakMethod: 'POST_JSON',
    speakParam: 'text',
    type: 'echo',
    interrupt: true
};

// 同步配置
const SYNC_CONFIG = {
    syncWithDashboard: true,    // 啟用同步
    sharedSessionId: null,      // 共享 Session ID
    syncInterval: 5000          // 檢查間隔
};
```

### 環境變數
```bash
export LT_UPSTREAM=http://localhost:8010  # LiveTalking 服務地址
```

## 同步控制 API

### JavaScript 控制函數
```javascript
// 設置同步模式
window.LT.setSyncMode(true/false);

// 同步到指定 Session
window.LT.syncToSession(sessionId);

// 獲取同步配置
const config = window.LT.getSyncConfig();
```

## 故障排除

### Q: 同步功能無法使用？
A: 檢查以下項目：
1. LiveTalking 服務是否在 8010 端口運行
2. 瀏覽器是否支援 localStorage
3. 網絡連接是否正常

### Q: 虛擬人顯示不一致？
A: 嘗試以下解決方案：
1. 點擊「立即同步」按鈕
2. 刷新兩個頁面
3. 重新啟動 LiveTalking 服務

### Q: Session ID 不更新？
A: 可能的原因：
1. 同步間隔尚未到達（默認 5 秒）
2. localStorage 被清除
3. 服務連接問題

### Q: 如何檢查同步狀態？
A: 在瀏覽器 Console 中執行：
```javascript
console.log('同步配置:', window.LT.getSyncConfig());
console.log('共享 Session:', localStorage.getItem('lt_shared_session_id'));
```

## 注意事項

1. **服務依賴**：同步功能需要 LiveTalking 服務正常運行
2. **瀏覽器支援**：需要支援 localStorage 和 WebRTC
3. **性能影響**：同步會增加少量網絡請求
4. **隱私考量**：Session ID 會保存在 localStorage 中

## 高級用法

### 自定義同步間隔
```javascript
// 修改同步檢查間隔為 3 秒
SYNC_CONFIG.syncInterval = 3000;
```

### 手動觸發同步
```javascript
// 在 Console 中手動同步
window.LT.syncToSession('your-session-id');
```

### 監聽同步事件
```javascript
// 監聽同步狀態變化
window.addEventListener('lt-sync-status-change', (event) => {
    console.log('同步狀態變化:', event.detail);
});
```

這個同步功能讓您可以在面試頁面和 Dashboard 之間無縫切換，同時保持虛擬人狀態的一致性，提供更好的用戶體驗。
