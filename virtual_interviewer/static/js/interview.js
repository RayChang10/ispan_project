/**
 * 虛擬面試顧問 - 面試頁面功能
 */

let currentUserId = null;
let isInterviewActive = false;
let chatHistory = [];
let currentStage = 'waiting'; // 當前面試階段: waiting, intro, intro_analysis, questioning, completed
let autoNextQuestion = true; // 新增自動下一題開關

// 面試階段配置
const INTERVIEW_STAGES = {
    waiting: { name: '等待開始', progress: 0, badge: 'bg-primary' },
    intro: { name: '自我介紹', progress: 25, badge: 'bg-info' },
    intro_analysis: { name: '介紹分析', progress: 50, badge: 'bg-warning' },
    questioning: { name: '面試問答', progress: 75, badge: 'bg-success' },
    completed: { name: '面試完成', progress: 100, badge: 'bg-secondary' }
};

// 面試管理器
const InterviewManager = {
    /**
     * 初始化面試介面
     */
    init: function () {
        console.log('🚀 InterviewManager 初始化開始');

        // 設置初始狀態
        currentStage = 'waiting';
        isInterviewActive = false;

        // 重置所有標記
        this._hasSentFirstQuestion = false;
        this._isGettingNextQuestion = false;

        this.bindEvents();
        this.loadChatHistory();
        this.checkMicrophonePermission();
        this.updateStageDisplay(); // 初始化階段顯示

        console.log('✅ InterviewManager 初始化完成');
    },

    /**
     * 綁定事件監聽器
     */
    bindEvents: function () {
        console.log('🔗 開始綁定事件監聽器');

        // 發送訊息按鈕
        $('#sendMessage').on('click', () => {
            this.sendMessage();
        });

        // Enter鍵發送訊息
        $('#messageInput').on('keypress', (e) => {
            if (e.which === 13 && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 開始面試按鈕
        $('#startInterview').on('click', (e) => {
            console.log('🎯 開始面試按鈕點擊事件觸發');
            e.preventDefault();
            this.startInterview();
        });

        // 重新開始按鈕
        $('#resetInterview').on('click', () => {
            this.resetInterview();
        });

        // 暫停按鈕
        $('#pauseInterview').on('click', () => {
            this.pauseInterview();
        });

        // 語音輸入按鈕
        $('#voiceInput').on('click', () => {
            this.toggleVoiceInput();
        });

        // 檔案上傳按鈕
        $('#fileUpload').on('click', () => {
            $('#fileInput').click();
        });

        // 檔案選擇事件
        $('#fileInput').on('change', (e) => {
            this.handleFileUpload(e.target.files[0]);
        });

        // 確認輸入按鈕
        $('#confirmInput').on('click', () => {
            this.confirmInput();
        });

        // 監聽輸入框變化
        $('#messageInput').on('input', () => {
            this.updateConfirmButton();
        });


    },

    /**
     * 發送訊息
     */
    sendMessage: function () {
        const message = $('#messageInput').val().trim();
        if (!message) return;

        // 檢查是否為重複的問題請求 - 加強檢測邏輯
        if (currentStage === 'questioning') {
            const isQuestionRequest = message.includes('請給我問題') ||
                message.includes('請給我第一個問題') ||
                message.includes('下一題') ||
                message.includes('下一個問題');

            if (isQuestionRequest && (this._isGettingNextQuestion || this._hasSentFirstQuestion)) {
                console.log('⚠️ 正在處理問題請求或已發送第一題，跳過重複輸入');
                $('#messageInput').val(''); // 清空輸入框
                this.displayMessage('系統正在準備問題，請稍候...', 'ai');
                return;
            }
        }

        // 顯示用戶訊息
        this.displayMessage(message, 'user');

        // 清空輸入框
        $('#messageInput').val('');
        this.updateConfirmButton();

        // 顯示AI正在思考
        this.showTypingIndicator();

        // 優先使用狀態控制的後端 API 處理面試流程
        this.sendToBackend(message);
    },

    /**
     * 發送到 MCP 伺服器
     */
    sendToMCP: function (message) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: 'http://localhost:8080/api/chat',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ message: message }),
                timeout: 5000,
                crossDomain: true
            }).done((response) => {
                console.log('MCP 回應:', response);
                resolve(response);
            }).fail((xhr, status, error) => {
                console.log('MCP 連接失敗，狀態:', status, '錯誤:', error);
                console.log('HTTP 狀態:', xhr.status, '回應:', xhr.responseText);
                reject(error);
            });
        });
    },

    /**
     * 發送到後端
     */
    sendToBackend: function (message) {
        // 直接發送請求，不再在這裡處理問題請求的延遲
        // 延遲邏輯已經移到 sendFirstQuestion 方法中處理
        this._sendActualRequest(message);
    },

    /**
     * 發送實際請求到後端
     */
    _sendActualRequest: function (message) {
        // 如果是面試完成階段，傳遞面試數據
        let requestData = {
            message: message,
            user_id: currentUserId || 'default_user'
        };

        // 如果是面試完成階段，傳遞面試數據
        if (currentStage === 'completed' || message.includes('結束') || message.includes('完成')) {
            requestData.interview_data = {
                chat_history: chatHistory,
                total_questions: chatHistory.filter(chat => chat.stage === 'questioning' && chat.user.includes('請給我問題')).length,
                average_score: this._calculateAverageScore(),
                stage: currentStage
            };
        }

        API.post('/interview', requestData).done((response) => {
            this.hideTypingIndicator();
            if (response.success) {
                this.displayMessage(response.response, 'ai');

                // 檢測並更新面試階段
                this.detectStageChange(response.response);

                // 儲存對話記錄
                chatHistory.push({
                    user: message,
                    ai: response.response,
                    timestamp: new Date().toISOString(),
                    tool_used: 'backend_api',
                    stage: currentStage
                });
                this.saveChatHistory();

                // 檢查是否為分析結果，如果是則等待5秒後自動獲取下一題
                // 只有在面試問答階段且是分析結果時才自動獲取下一題
                if (currentStage === 'questioning' && this._isAnalysisResult(response.response) && autoNextQuestion) {
                    console.log('🎯 檢測到分析結果，5秒後自動獲取下一題');

                    // 防止重複觸發
                    if (this._autoNextQuestionTimer) {
                        clearTimeout(this._autoNextQuestionTimer);
                    }

                    this._autoNextQuestionTimer = setTimeout(() => {
                        console.log('⏰ 自動獲取下一題計時器觸發');
                        this._autoGetNextQuestion();
                        this._autoNextQuestionTimer = null;
                    }, 5000);
                }
            } else {
                console.error('後端 API 失敗，嘗試 MCP:', response);
                this.fallbackToMCP(message);
            }
        }).fail((xhr) => {
            console.error('後端 API 連接失敗，嘗試 MCP:', xhr);
            this.fallbackToMCP(message);
        });
    },

    /**
     * 檢查是否為分析結果
     */
    _isAnalysisResult: function (response) {
        const analysisKeywords = [
            '評分：',
            '相似度：',
            '反饋：',
            '標準答案：',
            '具體差異：',
            'Score:',
            'Similarity:',
            'Feedback:',
            'Standard Answer:',
            'Specific Differences:',
            'MCP 工具分析結果',
            '分析結果',
            '評分:',
            '相似度:',
            '反饋:',
            '標準答案:',
            '具體差異:'
        ];

        return analysisKeywords.some(keyword => response.includes(keyword));
    },

    /**
     * 自動獲取下一題
     */
    _autoGetNextQuestion: function () {
        console.log('🎯 自動獲取下一題');

        // 防止重複調用 - 只檢查是否正在獲取問題
        if (this._isGettingNextQuestion) {
            console.log('⚠️ 正在獲取下一題，跳過重複調用');
            return;
        }

        this._isGettingNextQuestion = true;

        // 顯示打字指示器
        this.showTypingIndicator();

        // 直接調用 _sendDirectQuestionRequest
        this._sendDirectQuestionRequest();
    },

    /**
     * 直接發送問題請求（不經過 sendToBackend 的延遲處理）
     */
    _sendDirectQuestionRequest: function () {
        // 禁用輸入框
        $('#messageInput').prop('disabled', true);

        API.post('/interview', {
            message: '請給我問題',
            user_id: currentUserId || 'default_user'
        }).done((response) => {
            // 重新啟用輸入框
            $('#messageInput').prop('disabled', false);
            console.log('✅ 下一題回應:', response);
            this.hideTypingIndicator();
            this._isGettingNextQuestion = false;

            if (response.success) {
                this.displayMessage(response.response, 'ai');

                // 儲存對話記錄
                chatHistory.push({
                    user: '請給我問題',
                    ai: response.response,
                    timestamp: new Date().toISOString(),
                    tool_used: 'backend_api',
                    stage: currentStage
                });
                this.saveChatHistory();
            } else {
                console.error('獲取下一題失敗:', response);
                this.displayMessage('抱歉，無法獲取下一題。請稍後再試。', 'ai');
            }
        }).fail((xhr) => {
            this.hideTypingIndicator();
            this._isGettingNextQuestion = false;
            console.error('獲取下一題連接失敗:', xhr);
            this.displayMessage('抱歉，無法連接到服務。請檢查網路連接或稍後再試。', 'ai');
        });
    },

    /**
     * 回退到 MCP 伺服器
     */
    fallbackToMCP: function (message) {
        console.log('🔄 回退到 MCP 伺服器');
        this.sendToMCP(message).then((mcpResponse) => {
            console.log('✅ MCP 回應成功:', mcpResponse);

            if (mcpResponse && mcpResponse.response) {
                this.displayMessage(mcpResponse.response, 'ai');

                // 檢測並更新面試階段
                this.detectStageChange(mcpResponse.response);

                // 儲存對話記錄
                chatHistory.push({
                    user: message,
                    ai: mcpResponse.response,
                    timestamp: new Date().toISOString(),
                    tool_used: mcpResponse.tool_used || 'mcp',
                    stage: currentStage
                });
                this.saveChatHistory();

                // 檢查是否為分析結果，如果是則等待5秒後自動獲取下一題
                // 只有在面試問答階段且是分析結果時才自動獲取下一題
                if (currentStage === 'questioning' && this._isAnalysisResult(mcpResponse.response)) {
                    setTimeout(() => {
                        this._autoGetNextQuestion();
                    }, 5000);
                }
            } else {
                console.error('❌ MCP 回應格式錯誤');
                this.displayMessage('抱歉，系統暫時無法回應。請稍後再試。', 'ai');
            }
        }).catch((error) => {
            this.hideTypingIndicator();
            console.error('❌ MCP 連接也失敗:', error);
            this.displayMessage('抱歉，無法連接到服務。請檢查網路連接或稍後再試。', 'ai');
        });
    },

    /**
     * 顯示訊息
     */
    displayMessage: function (message, sender) {
        const timestamp = Utils.formatRelativeTime(new Date());
        const isUser = sender === 'user';
        const avatarUrl = isUser ?
            'https://via.placeholder.com/40x40/28a745/ffffff?text=U' :
            'https://via.placeholder.com/40x40/007bff/ffffff?text=AI';

        const messageHtml = `
            <div class="message ${isUser ? 'user-message' : 'ai-message'} mb-3 fade-in">
                <div class="d-flex align-items-start ${isUser ? 'flex-row-reverse' : ''}">
                    <div class="avatar ${isUser ? 'ms-3' : 'me-3'}">
                        <img src="${avatarUrl}" class="rounded-circle" width="40" height="40">
                    </div>
                    <div class="message-content">
                        <div class="bg-primary text-white rounded-3 p-3 ${isUser ? 'slide-in-right' : 'slide-in-left'}">
                            <p class="mb-0">${this.formatMessage(message)}</p>
                        </div>
                        <small class="text-muted ms-1">${timestamp}</small>
                    </div>
                </div>
            </div>
        `;

        $('#chatMessages').append(messageHtml);
        this.scrollToBottom();
    },

    /**
     * 格式化訊息內容
     */
    formatMessage: function (message) {
        // 簡單的文字格式化
        return message
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    },

    /**
     * 顯示打字指示器
     */
    showTypingIndicator: function () {
        const typingHtml = `
            <div class="typing-indicator message ai-message mb-3" id="typingIndicator">
                <div class="d-flex align-items-start">
                    <div class="avatar me-3">
                        <img src="https://via.placeholder.com/40x40/007bff/ffffff?text=AI" 
                             class="rounded-circle" width="40" height="40">
                    </div>
                    <div class="message-content">
                        <div class="bg-primary text-white rounded-3 p-3">
                            <div class="typing-animation">
                                <span></span><span></span><span></span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        $('#chatMessages').append(typingHtml);
        this.scrollToBottom();
    },

    /**
     * 隱藏打字指示器
     */
    hideTypingIndicator: function () {
        $('#typingIndicator').remove();
    },

    /**
     * 滾動到底部
     */
    scrollToBottom: function () {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    },

    /**
     * 開始面試
     */
    startInterview: function () {
        console.log('🎯 開始面試按鈕被點擊'); // 調試日誌

        if (isInterviewActive) {
            console.log('面試已經在進行中，跳過');
            return;
        }

        console.log('開始執行面試邏輯'); // 調試日誌

        isInterviewActive = true;
        currentStage = 'intro';

        // 重置所有標記
        this._hasSentFirstQuestion = false;
        this._isGettingNextQuestion = false;

        this.updateStageDisplay();

        // 更新按鈕狀態
        $('#startInterview').prop('disabled', true).html('<i class="fas fa-spinner fa-spin me-1"></i>面試中...');
        $('#pauseInterview').prop('disabled', false);

        // 發送開始面試訊息到後端 API，讓後端處理狀態轉換和回應
        this.sendToBackend('開始面試');

        // 顯示通知
        if (typeof Utils !== 'undefined' && Utils.showNotification) {
            Utils.showNotification('面試已開始，祝您順利！', 'success');
        } else {
            console.log('✅ 面試已開始，祝您順利！');
        }

        console.log('面試開始邏輯執行完成');
    },

    /**
     * 更新階段顯示
     */
    updateStageDisplay: function () {
        const stage = INTERVIEW_STAGES[currentStage];
        if (!stage) return;

        // 更新狀態徽章
        $('#interviewStatus').removeClass('bg-primary bg-info bg-warning bg-success bg-secondary bg-danger')
            .addClass(stage.badge)
            .html(`<i class="fas fa-circle me-1"></i>${stage.name}`);

        // 更新進度條
        $('#interviewProgress').css('width', `${stage.progress}%`);
        $('#progressText').text(`${stage.name} (${stage.progress}%)`);

        // 更新階段說明
        this.updateStageDescription();
    },

    /**
     * 更新階段說明
     */
    updateStageDescription: function () {
        const descriptions = {
            waiting: '點擊「開始面試」按鈕開始您的面試之旅',
            intro: '正在進行自我介紹，請完整介紹您的背景',
            intro_analysis: '正在分析您的自我介紹內容',
            questioning: '面試問答進行中，請認真回答每個問題',
            completed: '面試已完成，查看您的表現總結'
        };

        const desc = descriptions[currentStage] || '面試進行中...';
        $('#stageDescription').html(`
            <h6 class="mb-2">📋 當前階段</h6>
            <p class="mb-0 small">${desc}</p>
        `);
    },

    /**
     * 暫停面試
     */
    pauseInterview: function () {
        if (!isInterviewActive) return;

        if (confirm('確定要暫停面試嗎？')) {
            isInterviewActive = false;
            $('#startInterview').prop('disabled', false).html('<i class="fas fa-play me-1"></i>繼續面試');
            $('#pauseInterview').prop('disabled', true);

            this.displayMessage('面試已暫停。點擊「繼續面試」可以繼續。', 'ai');
            Utils.showNotification('面試已暫停', 'warning');
        }
    },

    /**
     * 重新開始面試
     */
    resetInterview: function () {
        if (confirm('確定要重新開始面試嗎？這將清除所有對話記錄。')) {
            isInterviewActive = false;
            currentStage = 'waiting';
            chatHistory = [];
            $('#chatMessages').empty();

            // 重置所有標記
            this._hasSentFirstQuestion = false;
            this._isGettingNextQuestion = false;

            // 重置按鈕狀態
            $('#startInterview').prop('disabled', false).html('<i class="fas fa-play me-1"></i>開始面試');
            $('#pauseInterview').prop('disabled', true);

            this.updateStageDisplay();

            // 顯示歡迎訊息
            this.displayMessage('歡迎使用虛擬面試顧問！我會幫助您進行模擬面試。請點擊「開始面試」開始您的面試之旅。', 'ai');

            this.saveChatHistory();
            Utils.showNotification('面試已重新開始', 'info');
        }
    },

    /**
     * 檢測階段變化
     */
    detectStageChange: function (aiResponse) {
        if (!aiResponse) return;

        const response = aiResponse.toLowerCase();

        // 檢測階段變化的關鍵字
        if (currentStage === 'intro' && (
            response.includes('自我介紹分析') ||
            response.includes('分析結果') ||
            response.includes('評估結果')
        )) {
            currentStage = 'intro_analysis';
            this.updateStageDisplay();
        }
        else if (currentStage === 'intro_analysis' && (
            response.includes('分析完成') ||
            response.includes('自我介紹分析') ||
            response.includes('建議') ||
            response.includes('改進建議')
        )) {
            currentStage = 'questioning';
            this.updateStageDisplay();

            // 直接發送第一個問題，sendFirstQuestion 方法會處理5秒延遲
            // 只有在還沒有發送過第一個問題時才發送
            console.log(`🔍 檢查第一個問題標記: _hasSentFirstQuestion = ${this._hasSentFirstQuestion}`);
            if (!this._hasSentFirstQuestion) {
                console.log('🎯 準備發送第一個問題');
                setTimeout(() => {
                    console.log('⏰ 分析完成，發送第一個問題');
                    this.sendFirstQuestion();
                }, 1000); // 只等待1秒讓用戶看到階段轉換
            } else {
                console.log('⚠️ 已經發送過第一個問題，跳過');
            }
        }
        else if (currentStage === 'questioning' && (
            response.includes('面試完成') ||
            response.includes('總結報告') ||
            response.includes('感謝您參與') ||
            response.includes('面試已結束')
        )) {
            currentStage = 'completed';
            this.updateStageDisplay();
            // 面試完成，更新按鈕狀態
            isInterviewActive = false;
            $('#startInterview').prop('disabled', false).html('<i class="fas fa-play me-1"></i>重新開始');
            $('#pauseInterview').prop('disabled', true);
        }
    },

    /**
     * 發送第一個面試問題
     */
    sendFirstQuestion: function () {
        console.log('🎯 發送第一個面試問題');

        // 防止重複調用
        if (this._hasSentFirstQuestion || this._isGettingNextQuestion) {
            console.log('⚠️ 已經發送過第一個問題或正在處理中，跳過重複調用');
            return;
        }

        this._hasSentFirstQuestion = true;
        this._isGettingNextQuestion = true;

        // 先顯示提示訊息
        this.displayMessage('5秒後將為您提供第一個面試問題...', 'ai');

        // 等待5秒後再發送實際問題
        setTimeout(() => {
            // 顯示打字指示器
            this.showTypingIndicator();

            // 統一使用 '請給我問題' 格式
            API.post('/interview', {
                message: '請給我問題',
                user_id: currentUserId || 'default_user'
            }).done((response) => {
                console.log('✅ 第一個問題回應:', response);
                this.hideTypingIndicator();
                this._isGettingNextQuestion = false; // 重置標記，允許後續自動下一題

                if (response.success) {
                    this.displayMessage(response.response, 'ai');

                    // 儲存對話記錄
                    chatHistory.push({
                        user: '請給我問題',
                        ai: response.response,
                        timestamp: new Date().toISOString(),
                        tool_used: 'backend_api',
                        stage: currentStage
                    });
                    this.saveChatHistory();
                } else {
                    console.error('獲取第一個問題失敗:', response);
                    this.displayMessage('抱歉，無法獲取面試問題。請稍後再試。', 'ai');
                }
            }).fail((xhr) => {
                this.hideTypingIndicator();
                this._isGettingNextQuestion = false; // 重置標記
                console.error('獲取第一個問題連接失敗:', xhr);
                this.displayMessage('抱歉，無法連接到服務。請檢查網路連接或稍後再試。', 'ai');
            });
        }, 5000);
    },

    /**
     * 切換語音輸入
     */
    toggleVoiceInput: function () {
        if (!this.speechRecognition) {
            Utils.showNotification('您的瀏覽器不支援語音識別功能', 'warning');
            return;
        }

        if (this.isListening) {
            this.stopVoiceInput();
        } else {
            this.startVoiceInput();
        }
    },

    /**
     * 開始語音輸入
     */
    startVoiceInput: function () {
        this.isListening = true;
        $('#voiceInput').removeClass('btn-outline-info').addClass('btn-danger').html('<i class="fas fa-stop me-1"></i>停止錄音');

        this.speechRecognition.start();
        Utils.showNotification('語音識別已開始，請開始說話...', 'info');
    },

    /**
     * 停止語音輸入
     */
    stopVoiceInput: function () {
        this.isListening = false;
        $('#voiceInput').removeClass('btn-danger').addClass('btn-outline-info').html('<i class="fas fa-microphone me-1"></i>語音輸入');

        if (this.speechRecognition) {
            this.speechRecognition.stop();
        }
    },

    /**
     * 檢查麥克風權限
     */
    checkMicrophonePermission: function () {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.speechRecognition = new SpeechRecognition();
            this.speechRecognition.continuous = false;
            this.speechRecognition.interimResults = false;
            this.speechRecognition.lang = 'zh-TW';

            this.speechRecognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                $('#messageInput').val(transcript);
                this.updateConfirmButton();
                this.stopVoiceInput();
                Utils.showNotification('語音識別完成', 'success');
            };

            this.speechRecognition.onerror = (event) => {
                this.stopVoiceInput();
                Utils.showNotification(`語音識別錯誤: ${event.error}`, 'danger');
            };

            this.speechRecognition.onend = () => {
                this.stopVoiceInput();
            };
        } else {
            $('#voiceInput').prop('disabled', true).attr('title', '瀏覽器不支援語音識別');
        }
    },

    /**
     * 處理檔案上傳
     */
    handleFileUpload: function (file) {
        if (!file) return;

        // 檢查檔案類型
        const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        if (!allowedTypes.includes(file.type)) {
            Utils.showNotification('請上傳PDF或Word文檔格式的履歷', 'warning');
            return;
        }

        // 檢查檔案大小 (5MB)
        if (file.size > 5 * 1024 * 1024) {
            Utils.showNotification('檔案大小不能超過5MB', 'warning');
            return;
        }

        Utils.showLoading('#fileUpload', '上傳中...');

        // 創建FormData
        const formData = new FormData();
        formData.append('file', file);

        // 上傳檔案
        $.ajax({
            url: '/api/upload',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false
        }).done((response) => {
            Utils.hideLoading('#fileUpload');
            if (response.success) {
                Utils.showNotification('履歷上傳成功！', 'success');
                this.displayMessage('我已經收到您的履歷檔案，正在分析中...', 'ai');

                // TODO: 處理解析後的履歷資料
                setTimeout(() => {
                    this.displayMessage('履歷分析完成！現在可以開始針對您的背景進行面試。', 'ai');
                }, 2000);
            }
        }).fail(() => {
            Utils.hideLoading('#fileUpload');
        });
    },

    /**
     * 確認輸入
     */
    confirmInput: function () {
        const message = $('#messageInput').val().trim();
        if (message) {
            this.sendMessage();
        }
    },

    /**
     * 更新確認按鈕狀態
     */
    updateConfirmButton: function () {
        const hasText = $('#messageInput').val().trim().length > 0;
        $('#confirmInput').prop('disabled', !hasText);
    },

    /**
     * 載入聊天記錄
     */
    loadChatHistory: function () {
        chatHistory = Storage.get('chatHistory', []);
        chatHistory.forEach(chat => {
            this.displayMessage(chat.user, 'user');
            this.displayMessage(chat.ai, 'ai');
        });
    },

    /**
     * 儲存聊天記錄
     */
    saveChatHistory: function () {
        Storage.set('chatHistory', chatHistory);
    },

    /**
     * 計算平均分數
     */
    _calculateAverageScore: function () {
        const scores = [];

        for (const chat of chatHistory) {
            if (chat.stage === 'questioning' && chat.ai) {
                const score = this._extractScoreFromResponse(chat.ai);
                if (score !== null) {
                    scores.push(score);
                }
            }
        }

        if (scores.length === 0) return 0;
        return scores.reduce((sum, score) => sum + score, 0) / scores.length;
    },

    /**
     * 從回應中提取分數
     */
    _extractScoreFromResponse: function (response) {
        // 匹配 "評分：XX/100" 或 "Score: XX/100" 模式
        const patterns = [
            /評分[：:]\s*(\d+)\/100/,
            /Score[：:]\s*(\d+)\/100/,
            /(\d+)\/100\s*[（(]/
        ];

        for (const pattern of patterns) {
            const match = response.match(pattern);
            if (match) {
                return parseInt(match[1]);
            }
        }

        return null;
    },


};

// 當文檔就緒時初始化
$(document).ready(function () {
    console.log('📱 頁面載入完成，開始初始化');

    // 確保jQuery和必要元素都已載入
    if (typeof $ === 'undefined') {
        console.error('❌ jQuery 未載入');
        return;
    }

    // 檢查關鍵元素是否存在
    if ($('#startInterview').length === 0) {
        console.error('❌ 開始面試按鈕未找到');
        return;
    }

    if ($('#chatMessages').length === 0) {
        console.error('❌ 聊天訊息區域未找到');
        return;
    }

    console.log('✅ 關鍵元素檢查通過，開始初始化 InterviewManager');

    InterviewManager.init();

    // 顯示歡迎訊息
    setTimeout(() => {
        InterviewManager.displayMessage('歡迎使用虛擬面試顧問！我會幫助您進行模擬面試。請點擊「開始面試」開始您的面試之旅。', 'ai');
    }, 500);

    // 添加打字動畫CSS
    const typingCSS = `
        <style>
        .typing-animation {
            display: flex;
            align-items: center;
            height: 20px;
        }
        .typing-animation span {
            height: 8px;
            width: 8px;
            background-color: white;
            border-radius: 50%;
            display: inline-block;
            margin: 0 2px;
            animation: typing 1.4s infinite ease-in-out;
        }
        .typing-animation span:nth-child(1) { animation-delay: -0.32s; }
        .typing-animation span:nth-child(2) { animation-delay: -0.16s; }
        .typing-animation span:nth-child(3) { animation-delay: 0s; }
        
        @keyframes typing {
            0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }
        </style>
    `;
    $('head').append(typingCSS);

    console.log('🎉 初始化完成');
}); 