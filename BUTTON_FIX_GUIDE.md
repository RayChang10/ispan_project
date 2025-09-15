# 按鈕顯示問題修復指南

## 問題描述
虛擬人區域的控制按鈕（開始面試、暫停面試、終止面試）沒有顯示。

## 原因分析
1. **布局高度問題**：虛擬人區域的 `height: 100%` 導致按鈕被擠到看不見的地方
2. **JavaScript 隱藏邏輯**：面試狀態管理函數可能在某些情況下隱藏按鈕
3. **CSS 衝突**：可能存在樣式衝突導致按鈕不可見

## 修復措施

### 1. 調整布局高度
```html
<!-- 從 height:100% 改為 height:auto -->
<div id="lt-wrapper" style="height:auto; display:flex; flex-direction:column;">
    <video style="height:420px;">  <!-- 固定高度 -->
```

### 2. 增加按鈕可見性保護
```html
<!-- 添加 !important 樣式確保按鈕可見 -->
<div class="actions" style="display:flex !important;">
    <button id="start" style="display:inline-block !important;">開始面試</button>
    <!-- ... 其他按鈕 -->
</div>
```

### 3. JavaScript 調試和強制顯示
```javascript
// 添加調試代碼，強制顯示按鈕
setTimeout(() => {
    const startBtn = $('#start');
    if (startBtn) {
        startBtn.style.display = 'inline-block';
        startBtn.style.visibility = 'visible';
    }
    // ... 其他按鈕
}, 1000);
```

### 4. 改善降級模式顯示
```html
<!-- 確保降級模式有正確的高度和顯示方式 -->
<div id="avatar-fallback" style="height:420px; display:flex; flex-direction:column; justify-content:center;">
```

## 驗證方法

### 瀏覽器檢查
1. 打開開發者工具 (F12)
2. 檢查 Console 是否有 "調試按鈕狀態" 的日誌
3. 查看按鈕元素的計算樣式

### 功能測試
1. 重新載入頁面
2. 檢查虛擬人區域下方是否有控制按鈕
3. 測試按鈕點擊功能是否正常

## 臨時解決方案
如果問題仍然存在，可以嘗試：

```javascript
// 在瀏覽器 Console 中執行
document.querySelectorAll('.actions button').forEach(btn => {
    btn.style.display = 'inline-block';
    btn.style.visibility = 'visible';
});
document.querySelector('.actions').style.display = 'flex';
```

## 長期優化建議

1. **分離關注點**：將按鈕控制邏輯與虛擬人服務分離
2. **改善狀態管理**：簡化按鈕顯示/隱藏的邏輯
3. **增加錯誤恢復**：當出現問題時能自動恢復按鈕顯示
4. **用戶體驗**：確保在任何情況下核心控制按鈕都可用

## 技術細節

### 修改的文件
- `frontend/app/interview.html` - 調整布局和添加強制顯示樣式
- `frontend/assets/js/interview.js` - 添加調試和強制顯示邏輯
- `frontend/app/lt-viewer.js` - 改善降級模式處理

### 關鍵樣式
```css
.actions {
    display: flex !important;
    gap: 10px;
    margin-top: 10px;
    padding: 10px;
    background: rgba(255,255,255,0.1);
    border-radius: 8px;
}

.actions button {
    display: inline-block !important;
    visibility: visible !important;
}
```

這個修復確保了無論虛擬人服務狀態如何，用戶都能看到和使用控制按鈕。
