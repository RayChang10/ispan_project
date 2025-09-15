# 面試階段按鈕更新

## 新增功能

### 1. 重新開始按鈕 (`restart-interview`)
- **位置**: 面試控制按鈕區域
- **樣式**: `button warning` (黃色警告樣式)
- **功能**: 重新開始整個面試流程
- **顯示時機**: 面試問答階段和結束階段

### 2. 退出面試按鈕 (`exit-interview`)
- **位置**: 面試控制按鈕區域
- **樣式**: `button danger` (紅色危險樣式)
- **功能**: 退出面試，不保存進度
- **顯示時機**: 面試問答階段和結束階段

## 按鈕狀態管理

### 等待階段 (`waiting`)
- 只顯示「開始面試」按鈕
- 隱藏其他所有按鈕

### 自介階段 (`intro`)
- 顯示「完成自介」和「重新開始」按鈕
- 隱藏面試控制按鈕

### 面試問答階段 (`questioning`)
- 顯示所有面試控制按鈕：
  - 重新開始 (變更為「重新開始」)
  - 暫停面試
  - 結束面試
  - 重新開始 (新增)
  - 退出面試 (新增)
- 隱藏自介按鈕

### 結束階段 (`finished`)
- 顯示「重新開始」和「退出面試」按鈕
- 隱藏暫停和結束按鈕

## 事件處理

### 重新開始按鈕
```javascript
restartInterviewBtn.addEventListener('click', () => {
    handleRestartCommand();
});
```

### 退出面試按鈕
```javascript
exitInterviewBtn.addEventListener('click', () => {
    if (confirm('確定要退出面試嗎？所有進度將不會保存。')) {
        // 停止計時器
        pauseTimer();
        
        // 重置所有狀態
        resetTimer();
        resetInterviewModePrompt();
        interviewEnded = false;
        userCompletedIntro = false;
        interviewStarted = false;
        
        // 清空聊天區域
        chat.innerHTML = '';
        
        // 重置階段
        window.InterviewStageManager.setStage('waiting');
        
        // 更新按鈕狀態
        setButtonsForStage('waiting');
        
        // 顯示退出訊息
        push('assistant', '👋 您已退出面試。\n\n💡 如需重新開始，請點擊「開始面試」按鈕。');
        
        // 更新徽章
        const badge = document.querySelector('.badge');
        if (badge) {
            badge.textContent = '步驟 3/3';
        }
    }
});
```

## 修改的文件

1. **frontend/app/interview.html**
   - 在第233-235行添加了新的按鈕元素

2. **frontend/assets/js/interview.js**
   - 更新了 `setButtonsForStage` 函數
   - 添加了新按鈕的事件處理邏輯
   - 在第1332-1370行添加了事件監聽器

## 測試建議

1. 點擊「開始面試」進入自介階段
2. 完成自介後進入面試問答階段
3. 在面試問答階段測試「重新開始」和「退出面試」按鈕
4. 確認按鈕在不同階段的正確顯示和隱藏
